"""Compliance — NSE/BSE/SEBI circulars RAG routes (NotebookLM-style research)."""
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.compliance_agent import research as compliance_research
from services.compliance_rag import compliance_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class ResearchRequest(BaseModel):
    question: str
    sources: Optional[List[str]] = None          # ["nse", "bse", "sebi"] — default all
    year_filter: Optional[int] = None            # e.g. 2023
    session_id: Optional[str] = None
    top_k: int = 10


@router.post("/research")
async def research_endpoint(req: ResearchRequest):
    """Ask the Compliance AI a question; returns answer + citations."""
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question must be at least 3 characters")
    result = await compliance_research(
        question=req.question.strip(),
        sources=req.sources,
        year_filter=req.year_filter,
        session_id=req.session_id,
        top_k=max(3, min(req.top_k, 25)),
    )
    return result


@router.get("/stats")
async def compliance_stats(request: Request):
    """Ingestion + vector-store stats for each source (for UI progress bar)."""
    db = request.app.db
    from datetime import datetime, timezone

    store_stats = compliance_router.stats()
    target_year = int(os.environ.get("COMPLIANCE_TARGET_START_YEAR", "2010"))
    current_year = datetime.now(timezone.utc).year
    total_years_span = max(1, current_year - target_year + 1)

    stats: dict = {}
    for src in ("nse", "bse", "sebi"):
        circular_count = await db.compliance_circulars.count_documents({"source": src})
        chunk_count_db = await db.compliance_chunks.count_documents({"source": src})
        state = await db.compliance_ingestion_state.find_one({"source": src}, {"_id": 0}) or {}

        # HONEST progress: distinct years with at least 1 ingested circular / target span
        year_pipeline = [
            {"$match": {"source": src, "year": {"$gte": target_year, "$lte": current_year}}},
            {"$group": {"_id": "$year"}},
        ]
        year_docs = await db.compliance_circulars.aggregate(year_pipeline).to_list(length=None)
        years_covered = len(year_docs)
        progress = round(100.0 * years_covered / total_years_span, 1) if total_years_span else 0.0

        stats[src] = {
            **store_stats.get(src, {}),
            "circular_count": circular_count,
            "total_chunks_in_db": chunk_count_db,
            "phase": state.get("phase", "idle"),
            "progress_pct": progress,
            "oldest_date": state.get("oldest_date_iso"),
            "newest_date": state.get("newest_date_iso"),
            "target_start_year": state.get("target_start_year", target_year),
            "years_covered": years_covered,
            "total_years_span": total_years_span,
            "cycle_count": state.get("cycle_count", 0),
            "last_cycle_at": state.get("last_cycle_at"),
            "last_new_ingest_at": state.get("last_new_ingest_at"),
            "started_at": state.get("started_at"),
            "errors_count": state.get("errors_count", 0),
            "last_error": state.get("last_error"),
        }

    overall_phase = (
        "backfill" if any(s["phase"] == "backfill" for s in stats.values())
        else "live" if all(s["phase"] == "live" for s in stats.values())
        else "idle"
    )
    totals = {
        "circulars": sum(s["circular_count"] for s in stats.values()),
        "chunks": sum(s["total_chunks_in_db"] for s in stats.values()),
        "avg_progress_pct": round(
            sum(s["progress_pct"] for s in stats.values()) / max(1, len(stats)), 1
        ),
    }
    return {"stores": stats, "sources": list(stats.keys()), "overall_phase": overall_phase, "totals": totals}


@router.get("/circulars")
async def list_circulars(
    request: Request,
    source: Optional[str] = None,
    year: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """List ingested circulars with filters (for sidebar preview)."""
    db = request.app.db
    query: dict = {}
    if source:
        query["source"] = source.lower()
    if year:
        query["year"] = year
    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    skip = max(0, (page - 1) * limit)
    limit = max(1, min(limit, 200))

    total = await db.compliance_circulars.count_documents(query)
    cursor = (
        db.compliance_circulars.find(query, {"_id": 0})
        .sort("date_iso", -1)
        .skip(skip)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    return {"total": total, "page": page, "limit": limit, "items": items}


@router.post("/rebuild")
async def rebuild_indexes(request: Request):
    """Manually rebuild all TF-IDF stores from MongoDB chunks."""
    db = request.app.db
    await compliance_router.build_all(db)
    return {"status": "rebuilt", "stats": compliance_router.stats()}


@router.post("/ingest-now")
async def trigger_ingest(request: Request):
    """Fire one ingestion cycle synchronously in a thread (does not wait)."""
    import threading
    from daemons.compliance_ingestion import _run_cycle
    import pymongo
    import os

    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    def _go():
        try:
            client = pymongo.MongoClient(mongo_url)
            _run_cycle(client[db_name])
            client.close()
        except Exception as e:
            logger.error(f"Manual compliance ingest failed: {e}")

    t = threading.Thread(target=_go, daemon=True, name="compliance-manual-ingest")
    t.start()
    return {"status": "started", "message": "Ingestion cycle running in background"}

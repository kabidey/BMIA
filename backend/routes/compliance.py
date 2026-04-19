"""Compliance — NSE/BSE/SEBI circulars RAG routes (NotebookLM-style research)."""
import logging
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
    """Ingestion + vector-store stats for each source."""
    db = request.app.db
    stats = compliance_router.stats()
    # Add Mongo counts
    for src in ("nse", "bse", "sebi"):
        stats[src]["circular_count"] = await db.compliance_circulars.count_documents({"source": src})
        stats[src]["total_chunks_in_db"] = await db.compliance_chunks.count_documents({"source": src})
    return {"stores": stats, "sources": list(stats.keys())}


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

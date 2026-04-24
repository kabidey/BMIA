"""Compliance — NSE/BSE/SEBI circulars RAG routes (NotebookLM-style research)."""
import io
import logging
import os
import re
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from services.compliance_agent import research as compliance_research
from services.compliance_rag import compliance_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


# ─── Bulk-upload config ──────────────────────────────────────────────────
# Max upload size in MB — user-friendly default; override via env.
BULK_UPLOAD_MAX_MB = int(os.environ.get("COMPLIANCE_BULK_UPLOAD_MAX_MB", "500"))
ALLOWED_SOURCES = ("nse", "bse", "sebi")

# Filename pattern:  "YYYY-MM-DD_<circ-no>_title.pdf" or "YYYY-MM-DD_title.pdf"
# Examples: "2023-08-14_CIR-2023-08_Insider-Trading.pdf" → date=2023-08-14, circ=CIR-2023-08
#           "2024-06-02_LODR-amendment.pdf"              → date=2024-06-02, circ=auto
_BULK_FNAME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})(?:_([A-Za-z0-9._/-]+?))?_(.+?)\.pdf$",
    re.IGNORECASE,
)


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
            "consecutive_no_data": state.get("consecutive_no_data", 0),
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


@router.post("/backfill-dates")
async def backfill_dates():
    """One-shot maintenance: re-parse date_str on rows with year=None using
    the improved _parse_date (handles RFC822 + ISO-with-T). Safe to re-run.

    Fixes rows ingested before the date-parsing fixes were deployed."""
    import pymongo
    from daemons.compliance_ingestion import _parse_date

    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    fixed = scanned = 0
    for doc in db.compliance_circulars.find(
        {"$or": [{"year": None}, {"year": {"$exists": False}}, {"date_iso": ""}]},
        {"_id": 1, "source": 1, "circular_no": 1, "date_str": 1, "url": 1, "ingested_at": 1},
    ):
        scanned += 1
        date_str = doc.get("date_str") or ""
        if not date_str and doc.get("url"):
            m = re.search(r"/(\d{8})-\d+", doc["url"])
            if m:
                date_str = m.group(1)
        dt = _parse_date(date_str)
        if not dt:
            continue
        patch = {"date_iso": dt.date().isoformat(), "year": dt.year}
        db.compliance_circulars.update_one({"_id": doc["_id"]}, {"$set": patch})
        db.compliance_chunks.update_many(
            {"source": doc["source"], "circular_no": doc["circular_no"]},
            {"$set": patch},
        )
        fixed += 1

    # Refresh per-source oldest/newest cursors
    for src in ("nse", "bse", "sebi"):
        newest = list(db.compliance_circulars.find(
            {"source": src, "date_iso": {"$ne": ""}}, {"date_iso": 1, "_id": 0},
        ).sort("date_iso", -1).limit(1))
        oldest = list(db.compliance_circulars.find(
            {"source": src, "date_iso": {"$ne": ""}}, {"date_iso": 1, "_id": 0},
        ).sort("date_iso", 1).limit(1))
        patch = {}
        if newest:
            patch["newest_date_iso"] = newest[0]["date_iso"]
        if oldest:
            patch["oldest_date_iso"] = oldest[0]["date_iso"]
        if patch:
            db.compliance_ingestion_state.update_one(
                {"source": src}, {"$set": patch}, upsert=True,
            )

    client.close()
    return {"status": "ok", "scanned": scanned, "fixed": fixed}


class ResetSourceRequest(BaseModel):
    source: str
    target_start_year: int = 1995
    force_from_today: bool = True


@router.post("/reset-source")
async def reset_source(req: ResetSourceRequest):
    """Reset a source's ingestion state so the worker resumes backfilling from
    `target_start_year`. Needed when the worker has prematurely transitioned
    to `live` mode with shallow coverage."""
    if req.source not in ("nse", "bse", "sebi"):
        raise HTTPException(400, f"source must be one of nse/bse/sebi, got {req.source}")
    import pymongo
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    update = {
        "phase": "backfill",
        "target_start_year": req.target_start_year,
        "consecutive_no_data": 0,
        "last_error": None,
    }
    if req.force_from_today:
        update["oldest_date_iso"] = datetime.now(timezone.utc).date().isoformat()
    r = db.compliance_ingestion_state.update_one(
        {"source": req.source}, {"$set": update}, upsert=True,
    )
    client.close()
    return {
        "status": "ok", "source": req.source,
        "matched": r.matched_count, "modified": r.modified_count,
        "new_state": update,
    }



# ══════════════════════════════════════════════════════════════════════════
# BULK UPLOAD — ingest a ZIP of PDFs straight into the RAG pipeline.
# Purpose: cloud IPs can't crawl NSE/BSE/SEBI historical archives reliably,
# but SMIFS compliance team almost certainly has years of PDFs on their
# file server. This endpoint accepts a zip → extracts → ingests each PDF
# via the same _ingest_pdf_bytes path the live scraper uses.
# ══════════════════════════════════════════════════════════════════════════

def _parse_bulk_filename(name: str) -> dict:
    """Extract (date_str, circ_no, title) from a filename if it follows the
    recommended `YYYY-MM-DD_<circ-no>_title.pdf` convention. Falls back to
    using the filename itself as the title with no date."""
    base = os.path.basename(name)
    m = _BULK_FNAME_RE.match(base)
    if m:
        date_str = m.group(1)                                 # YYYY-MM-DD
        circ_no = m.group(2) or base.rsplit(".", 1)[0][:80]   # auto if missing
        title = m.group(3).replace("-", " ").replace("_", " ").strip()
        return {"date_str": date_str, "circ_no": circ_no, "title": title}
    # Fallback: filename stem is the title, circ_no derived from stem
    stem = base.rsplit(".", 1)[0]
    return {"date_str": "", "circ_no": stem[:80], "title": stem.replace("-", " ").replace("_", " ").strip()}


def _run_bulk_job(job_id: str, source: str, zip_bytes: bytes):
    """Background worker: unzip, ingest each PDF, update job progress."""
    from pymongo import MongoClient
    from daemons.compliance_ingestion import _ingest_pdf_bytes, _rebuild_store
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    def _patch(**fields):
        db.compliance_bulkload_jobs.update_one(
            {"_id": job_id}, {"$set": {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        pdfs = [n for n in zf.namelist()
                if n.lower().endswith(".pdf") and not n.startswith("__MACOSX/")]
        total = len(pdfs)
        if total == 0:
            _patch(status="failed", error="ZIP contained no .pdf files", total=0)
            return

        _patch(status="running", total=total, processed=0, ingested=0, skipped=0, failed=0)
        ingested = skipped = failed = 0

        for i, name in enumerate(pdfs):
            try:
                meta = _parse_bulk_filename(name)
                pdf_bytes = zf.read(name)
                if not pdf_bytes or len(pdf_bytes) < 200:
                    skipped += 1
                    continue
                stored = _ingest_pdf_bytes(
                    db,
                    source=source,
                    circ_no=meta["circ_no"],
                    title=meta["title"],
                    date_str=meta["date_str"],
                    pdf_bytes=pdf_bytes,
                    category=f"bulk_upload_{source}",
                )
                if stored:
                    ingested += 1
                else:
                    skipped += 1
            except Exception as e:
                failed += 1
                logger.warning(f"BULK [{source}] {name}: {e}")
            # Persist progress every 5 files
            if (i + 1) % 5 == 0 or i == total - 1:
                _patch(processed=i + 1, ingested=ingested, skipped=skipped, failed=failed)

        # Rebuild TF-IDF once at the end — way more efficient than per-PDF
        _rebuild_store(db, source)
        _patch(
            status="done",
            processed=total,
            ingested=ingested,
            skipped=skipped,
            failed=failed,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"BULK UPLOAD [{source}] job {job_id}: done — {ingested} ingested, {skipped} skipped, {failed} failed")
    except Exception as e:
        logger.error(f"BULK UPLOAD [{source}] job {job_id} crashed: {e}")
        _patch(status="failed", error=str(e)[:500])
    finally:
        try:
            client.close()
        except Exception:
            pass


@router.post("/bulk-upload")
async def compliance_bulk_upload(
    request: Request,
    source: str = Form(...),
    file: UploadFile = File(...),
):
    """Kick off a bulk upload. Returns a job_id immediately; poll status via
    GET /api/compliance/bulk-upload/{job_id}.

    Filename convention inside the zip (optional but recommended):
      `YYYY-MM-DD_<circ-no>_title.pdf`
    """
    if source not in ALLOWED_SOURCES:
        raise HTTPException(status_code=400, detail=f"source must be one of {ALLOWED_SOURCES}")
    raw = await file.read()
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > BULK_UPLOAD_MAX_MB:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {BULK_UPLOAD_MAX_MB} MB limit ({size_mb:.1f} MB)")
    # Quick sanity — is it a valid zip?
    try:
        zipfile.ZipFile(io.BytesIO(raw)).testzip()
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive")

    db = request.app.db
    job_id = str(uuid.uuid4())
    await db.compliance_bulkload_jobs.insert_one({
        "_id": job_id,
        "source": source,
        "filename": file.filename,
        "size_mb": round(size_mb, 2),
        "status": "queued",
        "total": 0,
        "processed": 0,
        "ingested": 0,
        "skipped": 0,
        "failed": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    threading.Thread(
        target=_run_bulk_job, args=(job_id, source, raw),
        daemon=True, name=f"bulk-{source}-{job_id[:8]}",
    ).start()
    return {"job_id": job_id, "status": "queued", "source": source, "size_mb": round(size_mb, 2)}


@router.get("/bulk-upload/{job_id}")
async def compliance_bulk_upload_status(job_id: str, request: Request):
    doc = await request.app.db.compliance_bulkload_jobs.find_one({"_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    doc["job_id"] = doc.pop("_id")
    return doc


@router.get("/bulk-upload")
async def compliance_bulk_upload_list(request: Request, limit: int = 20):
    cursor = request.app.db.compliance_bulkload_jobs.find({}).sort("started_at", -1).limit(limit)
    jobs = []
    async for d in cursor:
        d["job_id"] = d.pop("_id")
        jobs.append(d)
    return {"jobs": jobs}

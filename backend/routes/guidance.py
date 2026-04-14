"""Guidance — BSE Corporate Announcements, AI RAG, PDF extraction, and Vector Store routes."""
import logging
import uuid
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.guidance_service import (
    get_guidance_items, get_guidance_stats, get_stock_list, run_full_scrape, prune_old_guidance,
)
from services.guidance_ai_service import ask_guidance_ai, get_suggested_questions
from services.pdf_extractor_service import process_unprocessed_pdfs, get_pdf_extraction_stats
from services.vector_store import guidance_vector_store
from services.briefing_service import get_daily_briefing, generate_daily_briefing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["guidance"])

_guidance_jobs = {}


class GuidanceAskRequest(BaseModel):
    question: str
    conversation_history: Optional[list] = None


@router.get("/guidance")
async def guidance_items(
    request: Request,
    symbol: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    db = request.app.db
    return await get_guidance_items(db, symbol=symbol, category=category, search=search, page=page, limit=limit)


@router.get("/guidance/stats")
async def guidance_stats(request: Request):
    db = request.app.db
    return await get_guidance_stats(db)


@router.get("/guidance/stocks")
async def guidance_stocks(request: Request):
    db = request.app.db
    stocks = await get_stock_list(db)
    return {"stocks": stocks, "total": len(stocks)}


@router.post("/guidance/scrape")
async def trigger_guidance_scrape(request: Request, days_back: int = 7):
    db = request.app.db
    job_id = str(uuid.uuid4())[:8]
    _guidance_jobs[job_id] = {"status": "running", "result": None, "error": None}

    async def _run():
        try:
            result = await run_full_scrape(db, days_back=days_back)
            _guidance_jobs[job_id]["status"] = "complete"
            _guidance_jobs[job_id]["result"] = result
        except Exception as e:
            _guidance_jobs[job_id]["status"] = "error"
            _guidance_jobs[job_id]["error"] = str(e)

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "started"}


@router.get("/guidance/scrape/{job_id}")
async def guidance_scrape_status(job_id: str):
    job = _guidance_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "complete" and job["result"]:
        response.update(job["result"])
        del _guidance_jobs[job_id]
    elif job["status"] == "error":
        response["error"] = job.get("error")
        del _guidance_jobs[job_id]
    return response


@router.post("/guidance/ask")
async def guidance_ask(req: GuidanceAskRequest, request: Request):
    db = request.app.db
    result = await ask_guidance_ai(db, req.question, req.conversation_history)
    return result


@router.get("/guidance/suggestions")
async def guidance_suggestions(request: Request):
    db = request.app.db
    suggestions = await get_suggested_questions(db)
    return {"suggestions": suggestions}


@router.get("/guidance/pdf/stats")
async def pdf_extraction_stats(request: Request):
    db = request.app.db
    return await get_pdf_extraction_stats(db)


@router.post("/guidance/pdf/process")
async def trigger_pdf_processing(request: Request, limit: int = 30):
    db = request.app.db
    result = await process_unprocessed_pdfs(db, limit=limit)
    return result


@router.get("/guidance/vectors/stats")
async def vector_store_stats():
    """Get vector store statistics."""
    return guidance_vector_store.get_stats()


@router.post("/guidance/vectors/rebuild")
async def rebuild_vector_store(request: Request):
    """Manually trigger vector store rebuild."""
    db = request.app.db
    await guidance_vector_store.build(db)
    return guidance_vector_store.get_stats()


@router.post("/guidance/prune")
async def trigger_prune(request: Request):
    """Manually prune guidance data older than 3 months."""
    db = request.app.db
    deleted = await prune_old_guidance(db)
    return {"pruned": deleted, "retention_days": 90}


@router.get("/guidance/briefing")
async def daily_briefing(request: Request):
    """Get auto-generated daily intelligence briefing (cached 6h)."""
    db = request.app.db
    return await get_daily_briefing(db)


@router.post("/guidance/briefing/refresh")
async def refresh_briefing(request: Request):
    """Force-regenerate the daily briefing."""
    db = request.app.db
    return await generate_daily_briefing(db)

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


@router.get("/guidance/stock/{symbol}/documents")
async def stock_documents(symbol: str, request: Request):
    """Get Screener.in-style categorized documents for a stock."""
    from datetime import datetime, timedelta, timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    cutoff = (datetime.now(IST) - timedelta(days=90)).isoformat()

    db = request.app.db

    # Fetch all docs for this stock in the 3-month window
    docs = await db.guidance.find(
        {
            "$or": [
                {"stock_symbol": {"$regex": f"^{symbol}$", "$options": "i"}},
                {"stock_name": {"$regex": symbol, "$options": "i"}},
                {"scrip_code": symbol},
            ],
            "scraped_at": {"$gte": cutoff},
        },
        {"_id": 0}
    ).sort("news_date", -1).to_list(length=500)

    if not docs:
        return {"symbol": symbol, "total": 0, "announcements": [], "annual_reports": [],
                "credit_ratings": [], "board_meetings": [], "results": [], "insider_activity": [],
                "agm_egm": [], "corporate_actions": []}

    # Categorize
    announcements_recent = []
    announcements_important = []
    annual_reports = []
    credit_ratings = []
    board_meetings = []
    results = []
    insider_activity = []
    agm_egm = []
    corporate_actions = []

    for d in docs:
        cat = (d.get("category") or "").lower()
        headline = (d.get("headline") or "").lower()
        item = {
            "news_id": d.get("news_id", ""),
            "headline": d.get("headline", ""),
            "category": d.get("category", "General"),
            "news_date": d.get("news_date", ""),
            "pdf_url": d.get("pdf_url"),
            "critical": d.get("critical", False),
            "more_text": (d.get("more_text", "") or "")[:300],
            "stock_symbol": d.get("stock_symbol", ""),
            "stock_name": d.get("stock_name", ""),
        }

        # Sort into categories (Screener.in style)
        if "annual report" in headline or "annual report" in cat:
            annual_reports.append(item)
        elif "credit rating" in headline or "rating" in cat or "credit" in headline:
            credit_ratings.append(item)
        elif "board meeting" in cat:
            board_meetings.append(item)
        elif "result" in cat:
            results.append(item)
        elif "insider" in cat or "sast" in cat:
            insider_activity.append(item)
        elif "agm" in cat or "egm" in cat:
            agm_egm.append(item)
        elif "corp" in cat and "action" in cat:
            corporate_actions.append(item)
        else:
            announcements_recent.append(item)

        # Mark important: critical filings + results + insider
        if d.get("critical") or "result" in cat or "insider" in cat or "sast" in cat:
            announcements_important.append(item)

    stock_name = docs[0].get("stock_name", "") if docs else ""
    scrip_code = docs[0].get("scrip_code", "") if docs else ""

    return {
        "symbol": symbol,
        "stock_name": stock_name,
        "scrip_code": scrip_code,
        "total": len(docs),
        "announcements": announcements_recent[:50],
        "important": announcements_important[:20],
        "annual_reports": annual_reports[:15],
        "credit_ratings": credit_ratings[:10],
        "board_meetings": board_meetings[:15],
        "results": results[:10],
        "insider_activity": insider_activity[:15],
        "agm_egm": agm_egm[:10],
        "corporate_actions": corporate_actions[:10],
        "bse_link": f"https://www.bseindia.com/stock-share-price/x/{symbol}/{scrip_code}/corp-announcements/" if scrip_code else None,
    }

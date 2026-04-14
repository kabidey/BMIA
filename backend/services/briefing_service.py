"""
Guidance Briefing Service — Auto-generated daily intelligence briefings.
Surfaces top critical filings, insider patterns, upcoming AGMs from the RAG vector store.
Cached in MongoDB, regenerated once daily or on demand.
"""
import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
BRIEFING_CACHE_HOURS = 6


async def _get_critical_filings(db, limit=5):
    """Get the most recent critical filings."""
    cutoff = (datetime.now(IST) - timedelta(days=90)).isoformat()
    docs = await db.guidance.find(
        {"critical": True, "scraped_at": {"$gte": cutoff}},
        {"_id": 0, "stock_symbol": 1, "stock_name": 1, "headline": 1,
         "category": 1, "news_date": 1, "pdf_url": 1}
    ).sort("news_date", -1).limit(limit).to_list(length=limit)
    return docs


async def _get_insider_activity(db, days=14, limit=10):
    """Get recent insider trading/SAST filings for pattern detection."""
    cutoff = (datetime.now(IST) - timedelta(days=days)).isoformat()
    docs = await db.guidance.find(
        {
            "category": {"$regex": "insider|sast", "$options": "i"},
            "scraped_at": {"$gte": cutoff},
        },
        {"_id": 0, "stock_symbol": 1, "stock_name": 1, "headline": 1,
         "news_date": 1, "critical": 1}
    ).sort("news_date", -1).limit(limit).to_list(length=limit)
    return docs


async def _get_upcoming_agms(db, limit=8):
    """Get upcoming AGM/EGM filings."""
    cutoff = (datetime.now(IST) - timedelta(days=30)).isoformat()
    docs = await db.guidance.find(
        {
            "category": {"$regex": "agm|egm", "$options": "i"},
            "scraped_at": {"$gte": cutoff},
        },
        {"_id": 0, "stock_symbol": 1, "stock_name": 1, "headline": 1,
         "news_date": 1, "pdf_url": 1}
    ).sort("news_date", -1).limit(limit).to_list(length=limit)
    return docs


async def _get_recent_board_meetings(db, limit=5):
    """Get recent board meeting outcomes."""
    cutoff = (datetime.now(IST) - timedelta(days=14)).isoformat()
    docs = await db.guidance.find(
        {
            "category": {"$regex": "board meeting", "$options": "i"},
            "scraped_at": {"$gte": cutoff},
        },
        {"_id": 0, "stock_symbol": 1, "stock_name": 1, "headline": 1,
         "news_date": 1, "critical": 1}
    ).sort("news_date", -1).limit(limit).to_list(length=limit)
    return docs


async def _generate_narrative(critical, insider, agms, board_meetings):
    """Use LLM to generate a brief morning narrative from the raw data."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return None

    context_parts = []

    if critical:
        context_parts.append("CRITICAL FILINGS:\n" + "\n".join(
            f"- {d.get('stock_symbol', '?')}: {d.get('headline', '')[:120]} [{d.get('news_date', '')[:10]}]"
            for d in critical
        ))

    if insider:
        context_parts.append("INSIDER TRADING/SAST:\n" + "\n".join(
            f"- {d.get('stock_symbol', '?')}: {d.get('headline', '')[:120]} [{d.get('news_date', '')[:10]}]"
            for d in insider
        ))

    if agms:
        context_parts.append("UPCOMING AGMs/EGMs:\n" + "\n".join(
            f"- {d.get('stock_symbol', '?')}: {d.get('headline', '')[:120]} [{d.get('news_date', '')[:10]}]"
            for d in agms
        ))

    if board_meetings:
        context_parts.append("RECENT BOARD MEETINGS:\n" + "\n".join(
            f"- {d.get('stock_symbol', '?')}: {d.get('headline', '')[:120]} [{d.get('news_date', '')[:10]}]"
            for d in board_meetings
        ))

    if not context_parts:
        return "No significant corporate filings to report today."

    prompt = (
        "You are the BMIA Morning Briefing writer. Write a concise (3-5 sentence) morning summary "
        "of the most important BSE corporate filings below. Highlight any red flags, opportunities, "
        "or notable patterns. Be direct and actionable — this goes on a trader's dashboard.\n\n"
        + "\n\n".join(context_parts)
        + "\n\nWrite ONLY the summary paragraph. No headers, no bullets, no greetings."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=api_key,
            session_id=f"briefing-{datetime.now(IST).strftime('%Y%m%d')}",
            system_message="You are a concise financial news summarizer for Indian equity markets.",
        )
        chat.with_model("openai", "gpt-4.1")
        response = await chat.send_message(UserMessage(text=prompt))
        return response.strip()
    except Exception as e:
        logger.error(f"BRIEFING: Narrative generation failed: {e}")
        return None


async def generate_daily_briefing(db):
    """Generate the full daily briefing with all sections + LLM narrative."""
    logger.info("BRIEFING: Generating daily briefing...")

    critical = await _get_critical_filings(db)
    insider = await _get_insider_activity(db)
    agms = await _get_upcoming_agms(db)
    board_meetings = await _get_recent_board_meetings(db)

    narrative = await _generate_narrative(critical, insider, agms, board_meetings)

    # Vector store stats
    try:
        from services.vector_store import guidance_vector_store
        vs_stats = guidance_vector_store.get_stats()
    except Exception:
        vs_stats = None

    # Aggregate stock-level filing counts (top movers by filing volume)
    cutoff_7d = (datetime.now(IST) - timedelta(days=7)).isoformat()
    pipeline = [
        {"$match": {"scraped_at": {"$gte": cutoff_7d}}},
        {"$group": {"_id": "$stock_symbol", "name": {"$first": "$stock_name"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_active = await db.guidance.aggregate(pipeline).to_list(length=5)
    top_active_stocks = [
        {"symbol": s["_id"], "name": s.get("name", ""), "filings_7d": s["count"]}
        for s in top_active if s["_id"]
    ]

    briefing = {
        "narrative": narrative,
        "critical_filings": critical,
        "insider_activity": insider,
        "upcoming_agms": agms,
        "board_meetings": board_meetings,
        "top_active_stocks": top_active_stocks,
        "vector_store": vs_stats,
        "generated_at": datetime.now(IST).isoformat(),
        "date": datetime.now(IST).strftime("%Y-%m-%d"),
    }

    # Cache in MongoDB
    await db.guidance_briefings.update_one(
        {"date": briefing["date"]},
        {"$set": briefing},
        upsert=True,
    )

    logger.info(f"BRIEFING: Generated — {len(critical)} critical, {len(insider)} insider, {len(agms)} AGMs")
    return briefing


async def get_daily_briefing(db):
    """Get the cached daily briefing, or generate if stale/missing."""
    today = datetime.now(IST).strftime("%Y-%m-%d")

    # Check cache
    cached = await db.guidance_briefings.find_one(
        {"date": today}, {"_id": 0}
    )

    if cached:
        generated_at = cached.get("generated_at", "")
        if generated_at:
            try:
                gen_time = datetime.fromisoformat(generated_at)
                age_hours = (datetime.now(IST) - gen_time).total_seconds() / 3600
                if age_hours < BRIEFING_CACHE_HOURS:
                    return cached
            except Exception:
                pass

    # Generate fresh briefing
    return await generate_daily_briefing(db)

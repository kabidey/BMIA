"""
Guidance Service — BSE Corporate Announcements Scraper
Fetches announcements, filings, PDFs for all BSE Group A stocks (covers NSE 500).
Runs daily at 5 AM IST via background scheduler.
3-month rolling window: data older than 90 days is pruned automatically.
"""
import logging
import time
import threading
import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
RETENTION_DAYS = 90  # 3-month rolling window

# BSE PDF base URL
BSE_PDF_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"


def _get_bse_session():
    """Create a fresh BSE session."""
    from bse import BSE
    return BSE(download_folder='/tmp')


def get_stock_universe():
    """Get BSE Group A securities (covers NSE 500 index stocks)."""
    try:
        bse = _get_bse_session()
        secs = bse.listSecurities(group='A')
        bse.exit()

        universe = []
        for s in secs:
            universe.append({
                "scrip_code": str(s.get("SCRIP_CD", "")),
                "name": s.get("Scrip_Name", ""),
                "symbol": s.get("scrip_id", ""),
                "isin": s.get("ISIN_NUMBER", ""),
                "group": s.get("GROUP", "A"),
                "status": s.get("Status", "Active"),
            })
        logger.info(f"GUIDANCE: Loaded {len(universe)} Group A stocks")
        return universe
    except Exception as e:
        logger.error(f"GUIDANCE: Failed to load universe: {e}")
        return []


def fetch_announcements_for_stock(scrip_code: str, days_back: int = 30):
    """Fetch BSE announcements for a single stock."""
    try:
        bse = _get_bse_session()
        to_date = date.today()
        from_date = to_date - timedelta(days=days_back)

        result = bse.announcements(
            scripcode=scrip_code,
            from_date=from_date,
            to_date=to_date,
        )
        bse.exit()

        announcements = []
        table = []
        if isinstance(result, dict):
            table = result.get("Table", [])
        elif isinstance(result, list):
            table = result

        for ann in table:
            attachment = ann.get("ATTACHMENTNAME", "")
            pdf_url = f"{BSE_PDF_BASE}/{attachment}" if attachment else None

            announcements.append({
                "news_id": ann.get("NEWSID", ""),
                "scrip_code": str(ann.get("SCRIP_CD", scrip_code)),
                "headline": ann.get("NEWSSUB", "").strip(),
                "category": ann.get("CATEGORYNAME", ann.get("ANNOUNCEMENT_TYPE", "General")),
                "news_date": ann.get("NEWS_DT", ""),
                "submission_date": ann.get("News_submission_dt", ann.get("DT_TM", "")),
                "pdf_url": pdf_url,
                "attachment_name": attachment,
                "attachment_size": ann.get("Fld_Attachsize", 0),
                "critical": ann.get("CRITICALNEWS", 0) == 1,
                "more_text": (ann.get("MORE", "") or "").strip()[:500],
            })

        return announcements
    except Exception as e:
        logger.error(f"GUIDANCE: Error fetching announcements for {scrip_code}: {e}")
        return []


async def prune_old_guidance(db):
    """Remove guidance documents older than RETENTION_DAYS (3 months).
    Returns count of deleted documents."""
    cutoff = (datetime.now(IST) - timedelta(days=RETENTION_DAYS)).isoformat()
    result = await db.guidance.delete_many({"scraped_at": {"$lt": cutoff}})
    deleted = result.deleted_count
    if deleted > 0:
        logger.info(f"GUIDANCE PRUNE: Removed {deleted} documents older than {RETENTION_DAYS} days")
    return deleted


async def run_full_scrape(db, days_back: int = 30, batch_size: int = 20):
    """
    Full scrape: fetch announcements for all Group A stocks.
    Stores results in MongoDB 'guidance' collection.
    After scraping, prunes data older than 3 months and rebuilds vector index.
    """
    universe = get_stock_universe()
    if not universe:
        return {"error": "Failed to load stock universe", "scraped": 0}

    total_scraped = 0
    total_stocks = len(universe)
    errors = []

    logger.info(f"GUIDANCE SCRAPE: Starting for {total_stocks} stocks, {days_back} days back")

    for i in range(0, total_stocks, batch_size):
        batch = universe[i:i + batch_size]

        for stock in batch:
            try:
                anns = fetch_announcements_for_stock(stock["scrip_code"], days_back)

                if anns:
                    for ann in anns:
                        ann["stock_name"] = stock["name"]
                        ann["stock_symbol"] = stock["symbol"]
                        ann["scraped_at"] = datetime.now(IST).isoformat()

                        # Upsert by news_id to avoid duplicates
                        await db.guidance.update_one(
                            {"news_id": ann["news_id"]},
                            {"$set": ann},
                            upsert=True,
                        )
                    total_scraped += len(anns)

            except Exception as e:
                errors.append(f"{stock['symbol']}: {str(e)}")

        # Rate limiting between batches
        progress = min(i + batch_size, total_stocks)
        logger.info(f"GUIDANCE SCRAPE: {progress}/{total_stocks} stocks processed, {total_scraped} announcements")
        if i + batch_size < total_stocks:
            time.sleep(2)

    # Create indexes for fast queries
    await db.guidance.create_index("scrip_code")
    await db.guidance.create_index("stock_symbol")
    await db.guidance.create_index("news_date")
    await db.guidance.create_index("category")
    await db.guidance.create_index("scraped_at")
    await db.guidance.create_index([("news_date", -1)])

    # Prune documents older than 3 months
    pruned = await prune_old_guidance(db)

    # Rebuild vector store after scrape
    try:
        from services.vector_store import guidance_vector_store
        await guidance_vector_store.build(db)
    except Exception as e:
        logger.error(f"GUIDANCE SCRAPE: Vector store rebuild failed: {e}")

    result = {
        "scraped": total_scraped,
        "stocks_processed": total_stocks,
        "pruned": pruned,
        "errors": len(errors),
        "error_details": errors[:20],
        "completed_at": datetime.now(IST).isoformat(),
    }
    logger.info(f"GUIDANCE SCRAPE COMPLETE: {total_scraped} announcements from {total_stocks} stocks, {pruned} pruned")
    return result


async def get_guidance_items(db, symbol: Optional[str] = None, category: Optional[str] = None,
                             search: Optional[str] = None, page: int = 1, limit: int = 50):
    """Query guidance items from MongoDB with filters. Enforces 3-month window."""
    cutoff = (datetime.now(IST) - timedelta(days=RETENTION_DAYS)).isoformat()
    query = {"scraped_at": {"$gte": cutoff}}

    if symbol:
        query["$or"] = [
            {"stock_symbol": {"$regex": symbol, "$options": "i"}},
            {"stock_name": {"$regex": symbol, "$options": "i"}},
            {"scrip_code": symbol},
        ]

    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    if search:
        query["headline"] = {"$regex": search, "$options": "i"}

    skip = (page - 1) * limit
    total = await db.guidance.count_documents(query)
    items = await db.guidance.find(query, {"_id": 0}).sort("news_date", -1).skip(skip).limit(limit).to_list(length=limit)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


async def get_guidance_stats(db):
    """Get summary stats for the Guidance page (3-month window only)."""
    cutoff = (datetime.now(IST) - timedelta(days=RETENTION_DAYS)).isoformat()
    base_filter = {"scraped_at": {"$gte": cutoff}}

    total = await db.guidance.count_documents(base_filter)
    pipeline_stocks = [
        {"$match": base_filter},
        {"$group": {"_id": "$stock_symbol"}},
    ]
    stocks_cursor = db.guidance.aggregate(pipeline_stocks)
    stocks_list = await stocks_cursor.to_list(length=5000)
    stock_count = len(stocks_list)

    # Category breakdown
    pipeline = [
        {"$match": base_filter},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 15},
    ]
    cat_cursor = db.guidance.aggregate(pipeline)
    categories = await cat_cursor.to_list(length=15)

    # Recent activity (last 7 days)
    week_ago = (datetime.now(IST) - timedelta(days=7)).isoformat()
    recent_count = await db.guidance.count_documents({"scraped_at": {"$gte": week_ago}})

    # Vector store stats
    try:
        from services.vector_store import guidance_vector_store
        vector_stats = guidance_vector_store.get_stats()
    except Exception:
        vector_stats = None

    return {
        "total_announcements": total,
        "total_stocks": stock_count,
        "categories": [{"name": c["_id"] or "Other", "count": c["count"]} for c in categories],
        "recent_7d": recent_count,
        "retention_days": RETENTION_DAYS,
        "vector_store": vector_stats,
    }


async def get_stock_list(db):
    """Get distinct stocks that have guidance data (3-month window)."""
    cutoff = (datetime.now(IST) - timedelta(days=RETENTION_DAYS)).isoformat()
    pipeline = [
        {"$match": {"scraped_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$stock_symbol",
            "name": {"$first": "$stock_name"},
            "scrip_code": {"$first": "$scrip_code"},
            "count": {"$sum": 1},
            "latest": {"$max": "$news_date"},
        }},
        {"$sort": {"count": -1}},
    ]
    cursor = db.guidance.aggregate(pipeline)
    stocks = await cursor.to_list(length=1000)
    return [{"symbol": s["_id"], "name": s["name"], "scrip_code": s["scrip_code"],
             "announcements": s["count"], "latest": s["latest"]} for s in stocks if s["_id"]]


# ── Daily Scheduler ──────────────────────────────────────────────────────────
def start_guidance_scheduler(mongo_url: str, db_name: str):
    """Start background thread that scrapes daily at 5 AM IST.
    Also prunes data older than 3 months and rebuilds vector index."""
    import asyncio as _aio
    from motor.motor_asyncio import AsyncIOMotorClient

    def _scheduler_loop():
        logger.info("GUIDANCE SCHEDULER: Started (daily at 5:00 AM IST, 3-month retention)")

        # Run initial scrape on first startup if DB is empty, then build vector store
        try:
            loop = _aio.new_event_loop()
            _aio.set_event_loop(loop)
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]

            count = loop.run_until_complete(db.guidance.count_documents({}))
            if count == 0:
                logger.info("GUIDANCE SCHEDULER: DB empty, running initial scrape (90 days)...")
                result = loop.run_until_complete(run_full_scrape(db, days_back=RETENTION_DAYS))
                logger.info(f"GUIDANCE SCHEDULER: Initial scrape done: {result.get('scraped', 0)} items")
            else:
                # Prune old data on startup
                pruned = loop.run_until_complete(prune_old_guidance(db))
                if pruned:
                    logger.info(f"GUIDANCE SCHEDULER: Startup prune removed {pruned} stale docs")

            # Build vector store on startup (skip if already built by lifespan)
            try:
                from services.vector_store import guidance_vector_store
                if not guidance_vector_store.is_ready:
                    loop.run_until_complete(guidance_vector_store.build(db))
            except Exception as e:
                logger.error(f"GUIDANCE SCHEDULER: Initial vector build failed: {e}")

            client.close()
            loop.close()
        except Exception as e:
            logger.error(f"GUIDANCE SCHEDULER: Initial scrape error: {e}")

        # Daily loop
        while True:
            try:
                now = datetime.now(IST)
                # Calculate next 5 AM IST
                target = now.replace(hour=5, minute=0, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)

                sleep_seconds = (target - now).total_seconds()
                logger.info(f"GUIDANCE SCHEDULER: Next scrape at {target.isoformat()}, sleeping {sleep_seconds/3600:.1f}h")
                time.sleep(sleep_seconds)

                # Run scrape (includes pruning + vector rebuild)
                loop = _aio.new_event_loop()
                _aio.set_event_loop(loop)
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]

                logger.info("GUIDANCE SCHEDULER: Running daily 5 AM scrape...")
                result = loop.run_until_complete(run_full_scrape(db, days_back=7))
                logger.info(f"GUIDANCE SCHEDULER: Daily scrape done: {result.get('scraped', 0)} items, {result.get('pruned', 0)} pruned")

                client.close()
                loop.close()
            except Exception as e:
                logger.error(f"GUIDANCE SCHEDULER: Error: {e}")
                time.sleep(3600)  # Retry in 1 hour on error

    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    logger.info("GUIDANCE SCHEDULER: Thread launched")

"""Market data routes — cockpit, overview, heatmap, snapshots."""
from fastapi import APIRouter, HTTPException, Request

from services.market_service import get_market_snapshot, get_ticker_info
from services.dashboard_service import get_full_cockpit, get_slow_cockpit_modules, get_cached_cockpit, get_cached_cockpit_slow
from daemons.market_cache import (
    ensure_bg_threads, get_cached_overview, set_overview_cache,
    get_cached_heatmap, set_heatmap_cache, _refresh_overview, _refresh_heatmap,
)

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/market/snapshot/{symbol}")
async def market_snapshot(symbol: str, period: str = "6mo", interval: str = "1d"):
    data = get_market_snapshot(symbol, period, interval)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/market/info/{symbol}")
async def market_info(symbol: str):
    data = get_ticker_info(symbol)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/market/overview")
async def market_overview():
    ensure_bg_threads()
    cached = get_cached_overview()
    if cached:
        return cached
    data = _refresh_overview()
    set_overview_cache(data)
    return data


@router.get("/market/heatmap")
async def market_heatmap():
    ensure_bg_threads()
    cached = get_cached_heatmap()
    if cached:
        return cached
    data = _refresh_heatmap()
    set_heatmap_cache(data)
    return data


@router.get("/market/cockpit")
async def market_cockpit():
    cached = get_cached_cockpit()
    if cached:
        return cached
    data = get_full_cockpit()
    return data


@router.get("/market/cockpit/slow")
async def market_cockpit_slow():
    cached = get_cached_cockpit_slow()
    if cached:
        return cached
    data = get_slow_cockpit_modules()
    return data


@router.get("/market/session")
async def market_session(request: Request):
    """Return market session status with holiday awareness from DB."""
    from datetime import datetime, timezone, timedelta
    import math

    db = request.app.db

    # Get IST now
    ist_offset = timedelta(hours=5, minutes=30)
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + ist_offset
    date_str = now_ist.strftime("%Y-%m-%d")
    day = now_ist.weekday()  # 0=Mon, 6=Sun
    h, m = now_ist.hour, now_ist.minute
    mins = h * 60 + m

    PRE_OPEN = 540       # 9:00
    MARKET_OPEN = 555    # 9:15
    MARKET_CLOSE = 930   # 15:30
    POST_CLOSE = 960     # 16:00

    is_weekend = day >= 5

    # Check holiday from DB
    holiday_doc = await db.nse_holidays.find_one({"date": date_str}, {"_id": 0})
    is_holiday = holiday_doc is not None
    holiday_name = holiday_doc.get("name", "Market Holiday") if holiday_doc else None

    # Find next trading day
    next_day = now_ist + timedelta(days=1)
    next_trading = None
    for _ in range(15):
        nd_str = next_day.strftime("%Y-%m-%d")
        nd_wd = next_day.weekday()
        hol = await db.nse_holidays.find_one({"date": nd_str})
        if nd_wd < 5 and not hol:
            next_trading = next_day.strftime("%a, %d %b")
            break
        next_day += timedelta(days=1)
    if not next_trading:
        next_trading = "next trading day"

    if is_holiday:
        return {"status": "holiday", "label": holiday_name, "sublabel": f"Opens {next_trading} 9:15 AM", "date": date_str}
    if is_weekend:
        return {"status": "closed", "label": "Weekend", "sublabel": f"Opens {next_trading} 9:15 AM", "date": date_str}
    if mins < PRE_OPEN:
        u = PRE_OPEN - mins
        return {"status": "premarket", "label": "Pre-Market", "sublabel": f"Opens in {u // 60}h {u % 60}m", "date": date_str}
    if mins < MARKET_OPEN:
        return {"status": "preopen", "label": "Pre-Open", "sublabel": f"Trading in {MARKET_OPEN - mins}m", "date": date_str}
    if mins < MARKET_CLOSE:
        u = MARKET_CLOSE - mins
        return {"status": "open", "label": "Market Open", "sublabel": f"Closes in {u // 60}h {u % 60}m", "date": date_str}
    if mins < POST_CLOSE:
        return {"status": "closing", "label": "Post-Close", "sublabel": "Closing auction", "date": date_str}
    return {"status": "closed", "label": "Market Closed", "sublabel": f"Opens {next_trading} 9:15 AM", "date": date_str}


@router.get("/market/holidays")
async def list_holidays(request: Request, year: int = None):
    """List all NSE holidays. Optionally filter by year."""
    db = request.app.db
    query = {}
    if year:
        query = {"date": {"$regex": f"^{year}"}}
    holidays = await db.nse_holidays.find(query, {"_id": 0}).sort("date", 1).to_list(length=100)
    return {"holidays": holidays, "total": len(holidays)}


@router.post("/market/holidays/seed")
async def seed_holidays(request: Request):
    """Seed NSE holidays for 2025-2027. Idempotent — skips existing."""
    db = request.app.db

    holidays = [
        # 2025
        ("2025-02-26", "Mahashivratri"), ("2025-03-14", "Holi"), ("2025-03-31", "Id-ul-Fitr"),
        ("2025-04-10", "Shri Mahavir Jayanti"), ("2025-04-14", "Dr. Ambedkar Jayanti"),
        ("2025-04-18", "Good Friday"), ("2025-05-01", "Maharashtra Day"),
        ("2025-06-07", "Bakri Id"), ("2025-08-15", "Independence Day"),
        ("2025-08-16", "Ashura"), ("2025-08-27", "Ganesh Chaturthi"),
        ("2025-10-02", "Mahatma Gandhi Jayanti"), ("2025-10-21", "Diwali Lakshmi Puja"),
        ("2025-10-22", "Diwali Balipratipada"), ("2025-11-05", "Guru Nanak Jayanti"),
        ("2025-12-25", "Christmas"),
        # 2026
        ("2026-01-26", "Republic Day"), ("2026-02-17", "Mahashivratri"),
        ("2026-03-03", "Holi"), ("2026-03-20", "Id-ul-Fitr"),
        ("2026-03-30", "Shri Mahavir Jayanti"), ("2026-04-03", "Good Friday"),
        ("2026-04-14", "Dr. Ambedkar Jayanti"), ("2026-05-01", "Maharashtra Day"),
        ("2026-05-28", "Bakri Id"), ("2026-06-25", "Muharram"),
        ("2026-08-15", "Independence Day"), ("2026-08-18", "Ganesh Chaturthi"),
        ("2026-08-25", "Eid-e-Milad"), ("2026-10-02", "Mahatma Gandhi Jayanti"),
        ("2026-10-09", "Dussehra"), ("2026-10-29", "Diwali Balipratipada"),
        ("2026-11-19", "Guru Nanak Jayanti"), ("2026-12-25", "Christmas"),
        # 2027
        ("2027-01-26", "Republic Day"), ("2027-03-11", "Id-ul-Fitr"),
        ("2027-03-22", "Holi"), ("2027-03-26", "Good Friday"),
        ("2027-04-14", "Dr. Ambedkar Jayanti"), ("2027-05-01", "Maharashtra Day"),
        ("2027-05-18", "Bakri Id"), ("2027-05-19", "Shri Mahavir Jayanti"),
        ("2027-06-15", "Muharram"), ("2027-08-14", "Eid-e-Milad"),
        ("2027-08-15", "Independence Day"), ("2027-09-07", "Ganesh Chaturthi"),
        ("2027-10-02", "Mahatma Gandhi Jayanti"), ("2027-10-18", "Diwali Lakshmi Puja"),
        ("2027-10-19", "Diwali Balipratipada"), ("2027-10-28", "Dussehra"),
        ("2027-11-09", "Guru Nanak Jayanti"), ("2027-12-25", "Christmas"),
    ]

    inserted = 0
    for date, name in holidays:
        existing = await db.nse_holidays.find_one({"date": date})
        if not existing:
            await db.nse_holidays.insert_one({"date": date, "name": name})
            inserted += 1

    return {"status": "seeded", "inserted": inserted, "total": len(holidays)}

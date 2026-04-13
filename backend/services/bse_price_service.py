"""
BSE Price Service — Fetches live price data from BSE India.
Uses the bse library for real-time quotes and market data.
Falls back to yfinance for historical data when needed.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# In-memory cache for BSE quotes (to avoid hammering BSE)
_quote_cache = {}
_cache_ttl = 60  # seconds


def _get_bse():
    from bse import BSE
    return BSE(download_folder='/tmp')


def get_bse_quote(scrip_code: str) -> dict:
    """Get live BSE quote for a stock."""
    cache_key = f"quote_{scrip_code}"
    cached = _quote_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _cache_ttl:
        return cached["data"]

    try:
        bse = _get_bse()
        q = bse.quote(scrip_code)
        bse.exit()

        if not q:
            return {}

        data = {
            "scrip_code": scrip_code,
            "prev_close": q.get("PrevClose", 0),
            "open": q.get("Open", 0),
            "high": q.get("High", 0),
            "low": q.get("Low", 0),
            "ltp": q.get("LTP", 0),
            "change": round(q.get("LTP", 0) - q.get("PrevClose", 0), 2) if q.get("LTP") and q.get("PrevClose") else 0,
            "change_pct": round(((q.get("LTP", 0) - q.get("PrevClose", 0)) / q.get("PrevClose", 1)) * 100, 2)
                          if q.get("PrevClose") else 0,
            "fetched_at": datetime.now(IST).isoformat(),
            "source": "bse",
        }

        _quote_cache[cache_key] = {"data": data, "ts": time.time()}
        return data

    except Exception as e:
        logger.error(f"BSE PRICE: Quote error for {scrip_code}: {e}")
        return {}


def get_bse_bulk_quotes(scrip_codes: list) -> list:
    """Get quotes for multiple stocks."""
    results = []
    for code in scrip_codes[:30]:  # Limit to 30 stocks
        q = get_bse_quote(str(code))
        if q:
            results.append(q)
        time.sleep(0.3)  # Rate limit
    return results


def get_bse_gainers() -> list:
    """Get top BSE gainers."""
    try:
        bse = _get_bse()
        data = bse.gainers(by="group", name="A")
        bse.exit()
        if isinstance(data, list):
            return data[:20]
        return data.get("Table", [])[:20] if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"BSE PRICE: Gainers error: {e}")
        return []


def get_bse_losers() -> list:
    """Get top BSE losers."""
    try:
        bse = _get_bse()
        data = bse.losers(by="group", name="A")
        bse.exit()
        if isinstance(data, list):
            return data[:20]
        return data.get("Table", [])[:20] if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"BSE PRICE: Losers error: {e}")
        return []


def get_bse_near_52w(type_: str = "high") -> list:
    """Get stocks near 52-week high/low."""
    try:
        bse = _get_bse()
        data = bse.near52WeekHighLow(by="group", name="A", dir_=type_)
        bse.exit()
        if isinstance(data, list):
            return data[:20]
        return data.get("Table", [])[:20] if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"BSE PRICE: 52W {type_} error: {e}")
        return []


def get_bse_advance_decline() -> dict:
    """Get BSE advance/decline data."""
    try:
        bse = _get_bse()
        data = bse.advanceDecline()
        bse.exit()
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"BSE PRICE: Advance/Decline error: {e}")
        return {}


async def get_scrip_code_map(db) -> dict:
    """Build a symbol-to-scrip_code mapping from guidance data."""
    pipeline = [
        {"$group": {"_id": "$stock_symbol", "scrip_code": {"$first": "$scrip_code"}}},
    ]
    cursor = db.guidance.aggregate(pipeline)
    results = await cursor.to_list(length=1000)
    return {r["_id"]: r["scrip_code"] for r in results if r["_id"] and r.get("scrip_code")}

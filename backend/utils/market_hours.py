"""
Centralized market-hours guard for portfolio operations.

Rule (non-negotiable): creation, rebalancing, and auto-reinvest must happen
during safe trading hours only — not at market edges.

Definition of SAFE WINDOW:
  - Monday-Friday only
  - Not an NSE holiday
  - IST time between 09:30 and 15:15 (skips first/last 15 min auction-heavy slots)

Usage:
  ok, reason = is_market_safe()
  if not ok:
      raise HTTPException(400, reason)
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# Market edges to avoid (auction volatility)
MARKET_OPEN = time(9, 15)       # NSE open
SAFE_OPEN = time(9, 30)         # +15 min buffer after open
SAFE_CLOSE = time(15, 15)       # -15 min buffer before close
MARKET_CLOSE = time(15, 30)     # NSE close

# Cached holiday set (YYYY-MM-DD strings) — loaded once from DB
_HOLIDAY_CACHE = {"set": None, "loaded_at": None}


def _load_holidays_sync(db_sync=None) -> set:
    """Load NSE holidays into memory. Cache for 6 hours."""
    now = datetime.now(IST)
    if _HOLIDAY_CACHE["set"] is not None and _HOLIDAY_CACHE["loaded_at"]:
        age = (now - _HOLIDAY_CACHE["loaded_at"]).total_seconds()
        if age < 21600:  # 6 hours
            return _HOLIDAY_CACHE["set"]

    holidays = set()
    if db_sync is not None:
        try:
            for h in db_sync.nse_holidays.find({}, {"_id": 0, "date": 1}):
                d = h.get("date")
                if d:
                    holidays.add(d)
        except Exception:
            pass

    # Fallback: known 2026 NSE holidays (extend as needed)
    if not holidays:
        holidays = {
            "2026-01-26", "2026-02-17", "2026-03-03", "2026-03-20",
            "2026-03-30", "2026-04-03", "2026-04-14", "2026-05-01",
            "2026-05-28", "2026-06-25", "2026-08-15", "2026-08-18",
            "2026-08-25", "2026-10-02", "2026-10-09", "2026-10-29",
            "2026-11-19", "2026-12-25",
        }

    _HOLIDAY_CACHE["set"] = holidays
    _HOLIDAY_CACHE["loaded_at"] = now
    return holidays


async def _load_holidays_async(db) -> set:
    """Async variant — loads from async Motor DB."""
    now = datetime.now(IST)
    if _HOLIDAY_CACHE["set"] is not None and _HOLIDAY_CACHE["loaded_at"]:
        age = (now - _HOLIDAY_CACHE["loaded_at"]).total_seconds()
        if age < 21600:
            return _HOLIDAY_CACHE["set"]

    holidays = set()
    try:
        cursor = db.nse_holidays.find({}, {"_id": 0, "date": 1})
        async for h in cursor:
            d = h.get("date")
            if d:
                holidays.add(d)
    except Exception:
        pass

    if not holidays:
        holidays = {
            "2026-01-26", "2026-02-17", "2026-03-03", "2026-03-20",
            "2026-03-30", "2026-04-03", "2026-04-14", "2026-05-01",
            "2026-05-28", "2026-06-25", "2026-08-15", "2026-08-18",
            "2026-08-25", "2026-10-02", "2026-10-09", "2026-10-29",
            "2026-11-19", "2026-12-25",
        }

    _HOLIDAY_CACHE["set"] = holidays
    _HOLIDAY_CACHE["loaded_at"] = now
    return holidays


def _check(now: datetime, holidays: set) -> tuple[bool, str]:
    """Shared logic: is `now` inside the safe trading window?"""
    # Weekend
    if now.weekday() >= 5:
        day = now.strftime("%A")
        return False, f"Market closed — it's {day}. Trades only Mon-Fri 09:30-15:15 IST."

    # Holiday
    today = now.strftime("%Y-%m-%d")
    if today in holidays:
        return False, f"Market closed — NSE holiday ({today}). Trades resume next business day 09:30 IST."

    # Time of day
    current = now.time()
    if current < MARKET_OPEN:
        return False, f"Market opens at 09:15 IST. Trading window: 09:30-15:15 IST (current {now.strftime('%H:%M')} IST)."
    if MARKET_OPEN <= current < SAFE_OPEN:
        return False, f"Too early — avoid 09:15-09:30 open auction. Trading window: 09:30-15:15 IST (current {now.strftime('%H:%M')} IST)."
    if SAFE_CLOSE <= current < MARKET_CLOSE:
        return False, f"Too late — avoid 15:15-15:30 close auction. Trading window: 09:30-15:15 IST (current {now.strftime('%H:%M')} IST)."
    if current >= MARKET_CLOSE:
        return False, f"Market closed at 15:30 IST. Trading window: 09:30-15:15 IST (current {now.strftime('%H:%M')} IST)."

    return True, "Market open (safe trading window)."


def is_market_safe_sync(db_sync=None) -> tuple[bool, str]:
    """Sync variant for daemon/scripts. Returns (ok, reason)."""
    now = datetime.now(IST)
    holidays = _load_holidays_sync(db_sync)
    return _check(now, holidays)


async def is_market_safe(db) -> tuple[bool, str]:
    """Async variant for FastAPI routes. Returns (ok, reason)."""
    now = datetime.now(IST)
    holidays = await _load_holidays_async(db)
    return _check(now, holidays)


def assert_market_safe_sync(db_sync=None):
    """Raise RuntimeError if not in safe window."""
    ok, reason = is_market_safe_sync(db_sync)
    if not ok:
        raise RuntimeError(f"Market hours guard: {reason}")


async def assert_market_safe(db):
    """Raise HTTPException 400 if not in safe window. Use in FastAPI routes."""
    from fastapi import HTTPException
    ok, reason = await is_market_safe(db)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

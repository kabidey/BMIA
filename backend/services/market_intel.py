"""
Market Intel Service — news + analyst estimates scrapers + calendar aggregator
for the Big Market dashboard. All functions are cache-wrapped (5-min TTL) and
degrade gracefully to empty payloads when sources block.
"""
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_CACHE: dict = {}
TTL_SEC = 300  # 5 minutes

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _cached(key: str, fn, ttl: int = TTL_SEC):
    now = time.time()
    hit = _CACHE.get(key)
    if hit and (now - hit["at"]) < ttl:
        return hit["data"]
    try:
        data = fn()
    except Exception as e:
        logger.debug(f"market_intel.{key} failed: {e}")
        data = None
    if data is not None:
        _CACHE[key] = {"at": now, "data": data}
        return data
    # Return stale cache if we have it, else empty
    return hit["data"] if hit else []


# ── 1. News (Moneycontrol + ET Markets, deduped) ─────────────────────────────
def _scrape_moneycontrol_news() -> list:
    url = "https://www.moneycontrol.com/rss/marketreports.xml"
    r = requests.get(url, headers=HEADERS, timeout=(5, 10))
    if r.status_code != 200:
        return []
    items = []
    # Simple RSS-ish parse
    for m in re.finditer(
        r"<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>",
        r.text, re.DOTALL,
    ):
        title, link, pub = m.group(1), m.group(2), m.group(3)
        items.append({
            "title": title.strip()[:300],
            "url": link.strip(),
            "published_at": pub.strip(),
            "category": "Markets",
        })
        if len(items) >= 30:
            break
    return items


def _scrape_et_markets_news() -> list:
    url = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
    r = requests.get(url, headers=HEADERS, timeout=(5, 10))
    if r.status_code != 200:
        return []
    items = []
    for m in re.finditer(
        r"<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>",
        r.text, re.DOTALL,
    ):
        title, link, pub = m.group(1), m.group(2), m.group(3)
        items.append({
            "title": title.strip()[:300],
            "url": link.strip(),
            "published_at": pub.strip(),
            "category": "Markets",
        })
        if len(items) >= 30:
            break
    return items


def get_market_news(limit: int = 25) -> list:
    def _fetch():
        items = _scrape_moneycontrol_news() + _scrape_et_markets_news()
        # Dedup by title prefix
        seen, out = set(), []
        for it in items:
            key = it["title"][:60].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        # Sort by pubDate desc (best-effort)
        def _ts(p):
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
                try:
                    return datetime.strptime(p, fmt).timestamp()
                except Exception:
                    continue
            return 0
        out.sort(key=lambda x: _ts(x.get("published_at", "")), reverse=True)
        return out
    data = _cached("news", _fetch) or []
    return data[:limit]


# ── 2. Analyst Estimates (Screener.in scrape) ────────────────────────────────
def get_analyst_estimates(symbol: str) -> dict:
    key = f"analyst:{symbol.upper()}"

    def _fetch():
        url = f"https://www.screener.in/company/{symbol.upper()}/consolidated/"
        r = requests.get(url, headers=HEADERS, timeout=(5, 12))
        if r.status_code != 200:
            return {}
        html = r.text
        out: dict = {"symbol": symbol.upper()}

        # CMP
        m = re.search(r"Current Price.*?₹([\d,]+\.?\d*)", html, re.DOTALL)
        if m:
            out["cmp"] = float(m.group(1).replace(",", ""))
        # PE, ROE, Market Cap basic ratios
        for label, key_out in [
            ("Stock P/E", "pe"), ("ROE", "roe"), ("Market Cap", "market_cap_cr"),
            ("Book Value", "book_value"), ("Dividend Yield", "div_yield"),
            ("Face Value", "face_value"), ("EPS", "eps"),
        ]:
            m = re.search(
                rf'<li[^>]*>\s*<span class="name">{re.escape(label)}.*?₹?\s*([\d,]+\.?\d*)',
                html, re.DOTALL,
            )
            if m:
                try:
                    out[key_out] = float(m.group(1).replace(",", ""))
                except Exception:
                    pass
        # Analyst recommendations block (if present)
        rec_match = re.search(
            r'Analyst Recommendations.*?Strong Buy.*?(\d+).*?Buy.*?(\d+).*?Hold.*?(\d+).*?Sell.*?(\d+).*?Strong Sell.*?(\d+)',
            html, re.DOTALL,
        )
        if rec_match:
            out["recommendations"] = {
                "strong_buy": int(rec_match.group(1)), "buy": int(rec_match.group(2)),
                "hold": int(rec_match.group(3)), "sell": int(rec_match.group(4)),
                "strong_sell": int(rec_match.group(5)),
            }
        return out

    return _cached(key, _fetch) or {"symbol": symbol.upper()}


# ── 3. Earnings / Events Calendar (BSE + NSE) ────────────────────────────────
async def get_earnings_calendar(db, days: int = 14) -> list:
    """Merge board-meeting announcements from BSE + upcoming NSE events."""
    from_date = datetime.now(timezone.utc) - timedelta(days=1)
    to_date = datetime.now(timezone.utc) + timedelta(days=days)

    # From our MongoDB (BSE announcements already ingested)
    bse_cursor = db.bse_announcements.find(
        {
            "category": {"$regex": "board|earnings|result|dividend", "$options": "i"},
            "date_iso": {
                "$gte": from_date.date().isoformat(),
                "$lte": to_date.date().isoformat(),
            },
        },
        {"_id": 0, "symbol": 1, "company_name": 1, "category": 1, "date_iso": 1, "title": 1},
    ).sort("date_iso", 1).limit(100)

    bse_events = []
    async for ev in bse_cursor:
        bse_events.append({
            "symbol": ev.get("symbol"),
            "company": ev.get("company_name", ""),
            "date": ev.get("date_iso"),
            "event_type": ev.get("category", "Board Meeting"),
            "title": ev.get("title", "")[:200],
        })

    # Also add NSE event calendar (best-effort, non-blocking)
    def _nse_events():
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            session.get("https://www.nseindia.com", timeout=(5, 8))
            time.sleep(0.5)
            r = session.get(
                "https://www.nseindia.com/api/event-calendar", timeout=(5, 10)
            )
            if r.status_code != 200:
                return []
            data = r.json()
            rows = data if isinstance(data, list) else data.get("data", [])
            out = []
            for row in rows[:200]:
                out.append({
                    "symbol": row.get("symbol"),
                    "company": row.get("company", ""),
                    "date": row.get("date", "")[:10],
                    "event_type": row.get("purpose", "Event"),
                    "title": row.get("bm_desc") or row.get("purpose", ""),
                })
            return out
        except Exception:
            return []

    nse_events = _cached("nse_events", _nse_events) or []

    # Dedup by (symbol, date, event_type)
    seen, merged = set(), []
    for ev in bse_events + nse_events:
        k = f"{ev.get('symbol')}|{ev.get('date')}|{ev.get('event_type')}"
        if k in seen:
            continue
        seen.add(k)
        merged.append(ev)
    merged.sort(key=lambda x: x.get("date") or "")
    return merged


# ── 4. PCR history (for sparkline) ───────────────────────────────────────────
def get_pcr_history(db, days: int = 30) -> dict:
    """Retrieve historical PCR values stored by the cockpit daemon."""
    # We don't persist PCR history right now — return current snapshot only
    from services.dashboard_service import get_pcr
    current = get_pcr() or {}
    return {"current": current, "history_days": days, "history": []}


# ── 5. Market movers formatted for scatter chart ─────────────────────────────
def get_market_movers_scatter() -> dict:
    """Format gainers/losers into scatter-compatible x/y/size payload."""
    from services.bse_price_service import get_bse_gainers, get_bse_losers
    from services.dashboard_service import get_volume_shockers

    def _fetch():
        gainers = get_bse_gainers() or []
        losers = get_bse_losers() or []
        shockers = get_volume_shockers() or {}
        shocker_list = shockers.get("shockers") if isinstance(shockers, dict) else shockers
        shocker_list = shocker_list or []

        def _row(r, kind):
            chg = r.get("percentChange") or r.get("pct_change") or r.get("chgPct") or 0
            vol = r.get("totalTradedVolume") or r.get("volume") or 0
            cap = r.get("marketCap") or r.get("market_cap") or 0
            return {
                "symbol": r.get("symbol") or r.get("scripCode") or r.get("script"),
                "company": r.get("companyName") or r.get("company") or "",
                "pct_change": float(chg or 0),
                "volume": int(vol or 0),
                "market_cap_cr": float(cap or 0),
                "kind": kind,
                "price": float(r.get("ltp") or r.get("price") or 0),
            }

        return {
            "gainers": [_row(r, "gainer") for r in gainers[:30]],
            "losers": [_row(r, "loser") for r in losers[:30]],
            "high_volume": [_row(r, "volume") for r in shocker_list[:20]],
        }
    return _cached("movers_scatter", _fetch) or {"gainers": [], "losers": [], "high_volume": []}

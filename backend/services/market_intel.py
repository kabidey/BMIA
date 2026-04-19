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
def _parse_rss_items(xml: str, max_items: int = 30) -> list:
    """Generic RSS <item> parser tolerant of whitespace and non-CDATA fields."""
    items: list = []
    for raw in re.findall(r"<item[^>]*>(.*?)</item>", xml, re.DOTALL):
        t = re.search(r"<title>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</title>", raw, re.DOTALL)
        lnk = re.search(r"<link>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</link>", raw, re.DOTALL)
        p = re.search(r"<pubDate>\s*(.*?)\s*</pubDate>", raw, re.DOTALL)
        if not (t and lnk):
            continue
        title = re.sub(r"\s+", " ", t.group(1)).strip()
        link = lnk.group(1).strip()
        pub = (p.group(1).strip() if p else "")
        if not title or not link:
            continue
        items.append({
            "title": title[:300],
            "url": link,
            "published_at": pub,
            "category": "Markets",
        })
        if len(items) >= max_items:
            break
    return items


def _scrape_rss(url: str) -> list:
    try:
        r = requests.get(url, headers=HEADERS, timeout=(5, 10))
        if r.status_code != 200:
            return []
        return _parse_rss_items(r.text)
    except Exception:
        return []


# RSS feeds — multi-source for resilience (cloud IPs may be blocked on some).
_NEWS_SOURCES = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.thehindubusinessline.com/markets/feeder/default.rss",
]


def get_market_news(limit: int = 25) -> list:
    def _fetch():
        items = []
        for url in _NEWS_SOURCES:
            items.extend(_scrape_rss(url))
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
            # Fall back to non-consolidated
            url = f"https://www.screener.in/company/{symbol.upper()}/"
            r = requests.get(url, headers=HEADERS, timeout=(5, 12))
            if r.status_code != 200:
                return {}
        html = r.text
        out: dict = {"symbol": symbol.upper()}

        # Screener renders ratios as:
        #   <li ...><span class="name">LABEL</span>... <span class="number">VALUE</span>...</li>
        ratio_pattern = re.compile(
            r'<li[^>]*>\s*<span class="name">\s*([^<]+?)\s*</span>'
            r'.*?<span class="number">([\d,.]+)</span>',
            re.DOTALL,
        )
        label_map = {
            "market cap": "market_cap_cr",
            "current price": "cmp",
            "stock p/e": "pe",
            "p/e": "pe",
            "book value": "book_value",
            "dividend yield": "div_yield",
            "roce": "roce",
            "roe": "roe",
            "face value": "face_value",
            "eps": "eps",
            "high / low": "high_low",
        }
        for m in ratio_pattern.finditer(html):
            label = m.group(1).strip().lower()
            val_str = m.group(2).replace(",", "")
            key_out = label_map.get(label)
            if not key_out:
                continue
            try:
                out[key_out] = float(val_str)
            except Exception:
                continue

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
    def _parse_event_date(s: str) -> str:
        """Normalize NSE event date ('02-May-2026' / '02-May-2026 00:00') → 'YYYY-MM-DD'."""
        if not s:
            return ""
        s = s.strip().split(" ")[0]
        for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except Exception:
                continue
        return s  # fall back to raw

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
            for row in rows[:300]:
                date_out = _parse_event_date(row.get("date") or "")
                out.append({
                    "symbol": row.get("symbol"),
                    "company": row.get("company", ""),
                    "date": date_out,
                    "event_type": row.get("purpose", "Event"),
                    "title": row.get("bm_desc") or row.get("purpose", ""),
                })
            return out
        except Exception as e:
            logger.debug(f"NSE event-calendar fetch failed: {e}")
            return []

    nse_events = _cached("nse_events", _nse_events) or []

    # Filter NSE events to the requested window (API returns a wider window).
    from_iso = from_date.date().isoformat()
    to_iso = to_date.date().isoformat()
    nse_events = [e for e in nse_events if e.get("date") and from_iso <= e["date"] <= to_iso]

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

        def _row_bse(r, kind):
            """BSE library fields: scripname, LONG_NAME, change_percent, trd_vol, ltradert, trd_val."""
            chg = r.get("change_percent")
            if chg is None:
                chg = r.get("percentChange") or r.get("pct_change") or r.get("chgPct") or 0
            vol = r.get("trd_vol") or r.get("totalTradedVolume") or r.get("volume") or 0
            price = r.get("ltradert") or r.get("ltp") or r.get("price") or 0
            # BSE doesn't return market cap in gainers feed; approximate "weight"
            # via traded value (in Rs lakhs) so scatter point size is non-zero.
            trd_val = r.get("trd_val") or 0
            return {
                "symbol": r.get("scripname") or r.get("symbol") or str(r.get("scrip_cd") or ""),
                "company": r.get("LONG_NAME") or r.get("companyName") or r.get("company") or "",
                "pct_change": float(chg or 0),
                "volume": int(vol or 0),
                "market_cap_cr": float(trd_val or 0),
                "kind": kind,
                "price": float(price or 0),
            }

        def _row_shocker(r, kind):
            return {
                "symbol": r.get("display_name") or r.get("symbol") or "",
                "company": r.get("display_name") or "",
                "pct_change": float(r.get("change_pct") or 0),
                "volume": int(r.get("volume") or 0),
                "market_cap_cr": float(r.get("volume") or 0) / 1e5,  # lakhs for size
                "kind": kind,
                "price": float(r.get("price") or 0),
            }

        return {
            "gainers": [_row_bse(r, "gainer") for r in gainers[:30] if r],
            "losers": [_row_bse(r, "loser") for r in losers[:30] if r],
            "high_volume": [_row_shocker(r, "volume") for r in shocker_list[:20] if r],
        }
    return _cached("movers_scatter", _fetch) or {"gainers": [], "losers": [], "high_volume": []}

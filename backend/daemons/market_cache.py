"""
Daemon: Background refresh for market overview & heatmap caches.
"""
import logging
import time
import threading
from datetime import datetime

from symbols import NIFTY_50, get_symbol_info
from services.market_service import get_market_snapshot

logger = logging.getLogger(__name__)

_overview_cache = {"data": None, "ts": 0}
_heatmap_cache = {"data": None, "ts": 0}
_OVERVIEW_TTL = 60

_bg_thread_started = False


def _refresh_overview():
    key_symbols = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LT.NS", "KOTAKBANK.NS",
        "SUNPHARMA.NS", "WIPRO.NS", "BAJFINANCE.NS", "MARUTI.NS", "HCLTECH.NS",
    ]
    movers = []
    for sym in key_symbols:
        try:
            data = get_market_snapshot(sym, "5d", "1d")
            if "error" not in data:
                info = get_symbol_info(sym)
                movers.append({
                    "symbol": sym,
                    "name": info["name"],
                    "sector": info["sector"],
                    "price": data["latest"]["close"],
                    "change": data["change"],
                    "change_pct": data["change_pct"],
                    "volume": data["latest"]["volume"],
                })
        except Exception as e:
            logger.error(f"Overview error for {sym}: {e}")
    movers.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    return {
        "gainers": movers[:5],
        "losers": movers[-5:][::-1] if len(movers) >= 5 else [],
        "all": movers,
        "timestamp": datetime.now().isoformat(),
    }


def _refresh_heatmap():
    heatmap = {}
    for sym_info in NIFTY_50[:30]:
        try:
            data = get_market_snapshot(sym_info["symbol"], "5d", "1d")
            if "error" not in data:
                sector = sym_info["sector"]
                if sector not in heatmap:
                    heatmap[sector] = []
                heatmap[sector].append({
                    "symbol": sym_info["symbol"],
                    "name": sym_info["name"],
                    "price": data["latest"]["close"],
                    "change_pct": data["change_pct"],
                    "volume": data["latest"]["volume"],
                })
        except Exception as e:
            logger.error(f"Heatmap error for {sym_info['symbol']}: {e}")
    return {"heatmap": heatmap, "timestamp": datetime.now().isoformat()}


def _bg_overview_heatmap_loop():
    while True:
        try:
            _overview_cache["data"] = _refresh_overview()
            _overview_cache["ts"] = time.time()
            logger.info("BG CACHE: Market overview refreshed")
        except Exception as e:
            logger.error(f"BG CACHE overview error: {e}")
        try:
            _heatmap_cache["data"] = _refresh_heatmap()
            _heatmap_cache["ts"] = time.time()
            logger.info("BG CACHE: Heatmap refreshed")
        except Exception as e:
            logger.error(f"BG CACHE heatmap error: {e}")
        time.sleep(60)


def ensure_bg_threads():
    global _bg_thread_started
    if not _bg_thread_started:
        _bg_thread_started = True
        t = threading.Thread(target=_bg_overview_heatmap_loop, daemon=True)
        t.start()
        logger.info("BG CACHE: Overview/heatmap background thread launched")


def get_cached_overview():
    if _overview_cache["data"] and (time.time() - _overview_cache["ts"]) < _OVERVIEW_TTL:
        return _overview_cache["data"]
    return None


def set_overview_cache(data):
    _overview_cache["data"] = data
    _overview_cache["ts"] = time.time()


def get_cached_heatmap():
    if _heatmap_cache["data"] and (time.time() - _heatmap_cache["ts"]) < _OVERVIEW_TTL:
        return _heatmap_cache["data"]
    return None


def set_heatmap_cache(data):
    _heatmap_cache["data"] = data
    _heatmap_cache["ts"] = time.time()

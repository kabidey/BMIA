"""
Market Data Service - Fetches OHLCV data using yfinance
"""
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

_cache = {}
CACHE_TTL = 300


def _cache_key(symbol, period, interval):
    return f"{symbol}_{period}_{interval}"


def _is_cached(key):
    if key in _cache:
        ts, data = _cache[key]
        if (datetime.now() - ts).total_seconds() < CACHE_TTL:
            return True
    return False


def get_market_snapshot(symbol: str, period: str = "6mo", interval: str = "1d"):
    key = _cache_key(symbol, period, interval)
    if _is_cached(key):
        return _cache[key][1]
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return {"error": f"No data for {symbol}", "symbol": symbol}
        
        ohlcv = []
        for idx, row in hist.iterrows():
            ohlcv.append({
                "time": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        
        latest = ohlcv[-1] if ohlcv else {}
        prev = ohlcv[-2] if len(ohlcv) > 1 else latest
        change = round(latest["close"] - prev["close"], 2) if latest and prev else 0
        change_pct = round((change / prev["close"] * 100), 2) if prev and prev["close"] else 0
        
        result = {
            "symbol": symbol,
            "latest": latest,
            "change": change,
            "change_pct": change_pct,
            "ohlcv": ohlcv,
            "data_points": len(ohlcv),
            "period": period,
            "interval": interval,
            "fetched_at": datetime.now().isoformat(),
        }
        
        _cache[key] = (datetime.now(), result)
        return result
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}


def get_ticker_info(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap"),
            "current_price": info.get("currentPrice") or info.get("previousClose"),
            "previous_close": info.get("previousClose"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
        }
    except Exception as e:
        logger.error(f"Error getting info for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}

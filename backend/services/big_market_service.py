"""
Big Market Service — Koyfin-style global market data aggregator.
Fetches indices, sectors, commodities, currencies, yields + Indian-specific KPIs.
All data from yfinance, cached for 5 minutes.
"""
import logging
import time
import math
import numpy as np
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
_cache = {"data": None, "ts": 0}
CACHE_TTL = 300  # 5 min


def _safe(val):
    if val is None:
        return None
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 2)
    except Exception:
        return None


def _fetch_ticker_data(symbol, period="1y", name=None):
    """Fetch price + KPIs for one ticker."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=period)
        if hist is None or len(hist) < 2:
            return None

        close = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        chg = round(close - prev, 2)
        chg_pct = round((chg / prev) * 100, 2) if prev else 0

        high_52w = _safe(hist["Close"].max())
        low_52w = _safe(hist["Close"].min())

        # Calculate returns
        def _ret(days):
            if len(hist) > days:
                old = float(hist["Close"].iloc[-days])
                return round((close - old) / old * 100, 2) if old else None
            return None

        # Z-Score (20-day)
        recent = hist["Close"].iloc[-21:] if len(hist) > 21 else hist["Close"]
        z_score = None
        if len(recent) > 5:
            mu = float(recent.mean())
            sigma = float(recent.std())
            if sigma > 0.001:
                z_score = round((close - mu) / sigma, 2)

        # YTD return
        ytd = None
        for i, idx in enumerate(hist.index):
            if idx.year == datetime.now().year:
                ytd = round((close - float(hist["Close"].iloc[i])) / float(hist["Close"].iloc[i]) * 100, 2)
                break

        # Volatility (annualized)
        returns = hist["Close"].pct_change().dropna()
        vol_1y = round(float(returns.std()) * math.sqrt(252) * 100, 2) if len(returns) > 20 else None

        # Volume
        vol = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else None
        avg_vol_10d = int(hist["Volume"].iloc[-11:-1].mean()) if len(hist) > 11 and "Volume" in hist.columns else None
        rel_vol = round(vol / avg_vol_10d, 1) if vol and avg_vol_10d and avg_vol_10d > 0 else None

        return {
            "symbol": symbol,
            "name": name or symbol,
            "price": round(close, 2),
            "change": chg,
            "change_pct": chg_pct,
            "z_score": z_score,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "ret_1m": _ret(21),
            "ret_3m": _ret(63),
            "ret_6m": _ret(126),
            "ret_ytd": ytd,
            "ret_1y": _ret(252),
            "volatility": vol_1y,
            "volume": vol,
            "avg_vol_10d": avg_vol_10d,
            "rel_vol": rel_vol,
        }
    except Exception as e:
        logger.debug(f"BigMarket fetch {symbol}: {e}")
        return None


INDIAN_INDICES = [
    ("^NSEI", "Nifty 50"), ("^BSESN", "Sensex"), ("^NSEBANK", "Bank Nifty"),
    ("^CNXIT", "Nifty IT"), ("^CNXPHARMA", "Nifty Pharma"), ("^CNXFMCG", "Nifty FMCG"),
    ("^CNXAUTO", "Nifty Auto"), ("^CNXMETAL", "Nifty Metal"), ("^CNXREALTY", "Nifty Realty"),
    ("^CNXENERGY", "Nifty Energy"), ("^CNXINFRA", "Nifty Infra"), ("^CNXPSUBANK", "Nifty PSU Bank"),
    ("^INDIAVIX", "India VIX"),
]

GLOBAL_INDICES = [
    ("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq Composite"), ("^DJI", "Dow Jones"),
    ("^RUT", "Russell 2000"), ("^GDAXI", "DAX"), ("^FTSE", "FTSE 100"),
    ("^FCHI", "CAC 40"), ("^N225", "Nikkei 225"), ("^HSI", "Hang Seng"),
    ("000001.SS", "Shanghai Composite"), ("^TWII", "Taiwan TAIEX"),
    ("^STI", "Straits Times"), ("^BVSP", "Ibovespa"), ("^GSPTSE", "S&P/TSX"),
    ("^VIX", "CBOE VIX"),
]

COMMODITIES = [
    ("GC=F", "Gold"), ("SI=F", "Silver"), ("CL=F", "Crude Oil WTI"),
    ("BZ=F", "Brent Crude"), ("NG=F", "Natural Gas"), ("HG=F", "Copper"),
    ("ALI=F", "Aluminum"),
]

CURRENCIES = [
    ("USDINR=X", "USD/INR"), ("EURINR=X", "EUR/INR"), ("GBPINR=X", "GBP/INR"),
    ("JPYINR=X", "JPY/INR"), ("EURUSD=X", "EUR/USD"), ("GBPUSD=X", "GBP/USD"),
    ("BTC-USD", "Bitcoin"),
]

YIELDS = [
    ("^IRX", "US 3M T-Bill"), ("^FVX", "US 5Y"), ("^TNX", "US 10Y"), ("^TYX", "US 30Y"),
]


def fetch_all_market_data():
    """Fetch all market data using parallel threads. Returns comprehensive dashboard data."""
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    logger.info("BIG MARKET: Fetching all market data...")
    start = time.time()

    all_tickers = []
    for group_name, tickers in [
        ("indian_indices", INDIAN_INDICES),
        ("global_indices", GLOBAL_INDICES),
        ("commodities", COMMODITIES),
        ("currencies", CURRENCIES),
        ("yields", YIELDS),
    ]:
        for sym, name in tickers:
            all_tickers.append((sym, name, group_name))

    results = {"indian_indices": [], "global_indices": [], "commodities": [],
               "currencies": [], "yields": []}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_fetch_ticker_data, sym, "1y", name): (sym, name, group)
            for sym, name, group in all_tickers
        }
        for future in as_completed(futures, timeout=30):
            sym, name, group = futures[future]
            try:
                data = future.result(timeout=10)
                if data:
                    results[group].append(data)
            except Exception:
                pass

    # Sort each group by change_pct descending
    for key in results:
        results[key].sort(key=lambda x: x.get("change_pct", 0) or 0, reverse=True)

    # Factor grid (Indian context): Value/Core/Growth × Large/Mid/Small
    factor_grid = _build_factor_grid(results.get("indian_indices", []))

    # Performance rankings (1Y return sorted)
    all_indices = results["indian_indices"] + results["global_indices"]
    perf_rankings = sorted(
        [{"name": d["name"], "ret_1y": d.get("ret_1y")} for d in all_indices if d.get("ret_1y") is not None],
        key=lambda x: x["ret_1y"], reverse=True
    )

    # Market breadth from Nifty data
    nifty_data = next((d for d in results["indian_indices"] if "Nifty 50" in d["name"]), None)

    data = {
        **results,
        "factor_grid": factor_grid,
        "perf_rankings": perf_rankings[:20],
        "market_breadth": {
            "nifty_chg_pct": nifty_data["change_pct"] if nifty_data else None,
            "india_vix": next((d["price"] for d in results["indian_indices"] if "VIX" in d["name"]), None),
        },
        "fetched_at": datetime.now(IST).isoformat(),
        "fetch_time_sec": round(time.time() - start, 1),
    }

    _cache["data"] = data
    _cache["ts"] = now
    logger.info(f"BIG MARKET: Fetched {sum(len(v) for v in results.values())} tickers in {time.time()-start:.1f}s")
    return data


def _build_factor_grid(indian_indices):
    """Build a Value/Core/Growth × Large/Mid/Small factor grid."""
    nifty = next((d for d in indian_indices if "Nifty 50" in d.get("name", "")), None)
    bank = next((d for d in indian_indices if "Bank" in d.get("name", "")), None)
    it = next((d for d in indian_indices if "IT" in d.get("name", "")), None)
    pharma = next((d for d in indian_indices if "Pharma" in d.get("name", "")), None)
    fmcg = next((d for d in indian_indices if "FMCG" in d.get("name", "")), None)
    auto = next((d for d in indian_indices if "Auto" in d.get("name", "")), None)
    metal = next((d for d in indian_indices if "Metal" in d.get("name", "")), None)
    realty = next((d for d in indian_indices if "Realty" in d.get("name", "")), None)
    psu = next((d for d in indian_indices if "PSU" in d.get("name", "")), None)

    def _pct(d):
        return f"{d['change_pct']}%" if d else "-"

    return {
        "headers": ["Value", "Core", "Growth"],
        "rows": [
            {"label": "Large", "cells": [
                _pct(bank), _pct(nifty), _pct(it)
            ]},
            {"label": "Mid", "cells": [
                _pct(psu), _pct(auto), _pct(pharma)
            ]},
            {"label": "Small", "cells": [
                _pct(metal), _pct(realty), _pct(fmcg)
            ]},
        ],
    }


def fetch_stock_snapshot(symbol):
    """Fetch Koyfin-style stock snapshot for a single security."""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        hist = t.history(period="1y")
        if hist is None or len(hist) < 2:
            return None

        close = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])

        # Performance returns
        def _ret(days):
            if len(hist) > days:
                old = float(hist["Close"].iloc[-days])
                return round((close - old) / old * 100, 2) if old else None
            return None

        returns = hist["Close"].pct_change().dropna()
        vol_1y = round(float(returns.std()) * math.sqrt(252) * 100, 2) if len(returns) > 20 else None

        # Chart data (for snapshot chart)
        chart_data = []
        for ts, row in hist.iterrows():
            chart_data.append({
                "date": ts.strftime("%Y-%m-%d"),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if "Volume" in row else 0,
            })

        # Key Data
        key_data = {
            "dividend_yield": _safe(info.get("dividendYield", 0) * 100) if info.get("dividendYield") else None,
            "beta": _safe(info.get("beta")),
            "shares_outstanding": info.get("sharesOutstanding"),
            "avg_volume_10d": info.get("averageDailyVolume10Day"),
            "volatility_1y": vol_1y,
            "short_interest_pct": _safe(info.get("shortPercentOfFloat", 0) * 100) if info.get("shortPercentOfFloat") else None,
            "industry": info.get("industry", ""),
            "sector": info.get("sector", ""),
        }

        # Valuation
        valuation = {
            "pe_trailing": _safe(info.get("trailingPE")),
            "pe_forward": _safe(info.get("forwardPE")),
            "pb": _safe(info.get("priceToBook")),
            "ev_sales": _safe(info.get("enterpriseToRevenue")),
            "ev_ebitda": _safe(info.get("enterpriseToEbitda")),
        }

        # Capital Structure
        capital = {
            "market_cap": info.get("marketCap"),
            "total_debt": info.get("totalDebt"),
            "cash": info.get("totalCash"),
            "enterprise_value": info.get("enterpriseValue"),
        }

        # Performance Returns
        perf = {
            "ret_1m": _ret(21),
            "ret_3m": _ret(63),
            "ret_ytd": _ret(min(len(hist) - 1, 252)),
            "ret_1y": _ret(252) if len(hist) > 252 else None,
        }

        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", "INR"),
            "price": round(close, 2),
            "change": round(close - prev, 2),
            "change_pct": round((close - prev) / prev * 100, 2),
            "high_52w": _safe(info.get("fiftyTwoWeekHigh")),
            "low_52w": _safe(info.get("fiftyTwoWeekLow")),
            "key_data": key_data,
            "valuation": valuation,
            "capital_structure": capital,
            "performance": perf,
            "chart_data": chart_data[-252:],
            "fetched_at": datetime.now(IST).isoformat(),
        }
    except Exception as e:
        logger.error(f"Stock snapshot {symbol}: {e}")
        return None

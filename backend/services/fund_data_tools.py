"""Data-fetch helpers used by the Fund Management 6-agent pipeline.

Each tool is small, fail-soft and returns a dict shaped for the agent prompts.
Reuses BMIA's existing data plumbing wherever possible (FII/DII, news, etc.)
and falls back to yfinance for OHLCV + fundamentals not covered elsewhere.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pymongo

logger = logging.getLogger(__name__)


# ─── Symbol helpers (NSE/BSE) ──────────────────────────────────────────────
def _yf_ticker(symbol: str) -> str:
    """Map a free-text symbol to yfinance format. Defaults to NSE (.NS) if no
    suffix is provided. Caller can pass `RELIANCE`, `RELIANCE.NS`, `500325.BO`, etc."""
    s = symbol.strip().upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    if s.isdigit():            # 6-digit BSE numeric code
        return f"{s}.BO"
    return f"{s}.NS"


# ─── Tool 1: Fundamentals (yfinance) ───────────────────────────────────────
def fetch_fundamentals(symbol: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
        t = yf.Ticker(_yf_ticker(symbol))
        info = t.info or {}
        return {
            "name": info.get("longName") or info.get("shortName") or symbol,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "pe_ttm": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margins": info.get("profitMargins"),
            "ebitda_margins": info.get("ebitdaMargins"),
            "currency": info.get("currency"),
            "ok": True,
        }
    except Exception as e:
        logger.warning(f"FUND fundamentals fetch failed for {symbol}: {e}")
        return {"ok": False, "error": str(e)[:160]}


# ─── Tool 2: Technicals (yfinance OHLCV + indicators) ──────────────────────
def fetch_technicals(symbol: str, period: str = "6mo") -> Dict[str, Any]:
    try:
        import numpy as np
        import yfinance as yf
        df = yf.Ticker(_yf_ticker(symbol)).history(period=period, auto_adjust=True)
        if df.empty:
            return {"ok": False, "error": "no_history"}
        close = df["Close"]
        last = float(close.iloc[-1])
        sma20 = float(close.tail(20).mean())
        sma50 = float(close.tail(50).mean()) if len(close) >= 50 else None
        sma200 = float(close.tail(200).mean()) if len(close) >= 200 else None
        # 14-period RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
        rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and not np.isnan(loss) and loss > 0 else None
        # Volatility (annualised)
        ret = close.pct_change().dropna()
        vol_ann = float(ret.std() * (252 ** 0.5)) if len(ret) > 5 else None
        high_52w = float(close.tail(252).max()) if len(close) >= 30 else float(close.max())
        low_52w = float(close.tail(252).min()) if len(close) >= 30 else float(close.min())
        return {
            "ok": True,
            "last_close": round(last, 2),
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2) if sma50 else None,
            "sma200": round(sma200, 2) if sma200 else None,
            "rsi14": round(float(rsi), 1) if rsi is not None else None,
            "ann_volatility_pct": round(vol_ann * 100, 1) if vol_ann else None,
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "pct_off_52w_high": round((1 - last / high_52w) * 100, 1) if high_52w else None,
            "trend": (
                "uptrend" if sma50 and last > sma50 > (sma200 or sma50) else
                "downtrend" if sma50 and last < sma50 else "sideways"
            ),
        }
    except Exception as e:
        logger.warning(f"FUND technicals fetch failed for {symbol}: {e}")
        return {"ok": False, "error": str(e)[:160]}


# ─── Tool 3: Sentiment (FII/DII + PCR from BMIA's big_market collections) ──
def fetch_sentiment(db) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": True}
    try:
        # Latest FII/DII row
        fii = db.fii_dii.find_one({}, {"_id": 0}, sort=[("date", -1)])
        if fii:
            out["fii_dii_latest"] = {k: fii.get(k) for k in
                                     ("date", "fii_net", "dii_net", "fii_buy", "fii_sell")}
        # Last 5 days net flows
        out["fii_dii_5d"] = list(db.fii_dii.find({}, {"_id": 0, "date": 1, "fii_net": 1, "dii_net": 1})
                                  .sort("date", -1).limit(5))
        # PCR snapshot
        pcr = db.pcr_snapshots.find_one({}, {"_id": 0}, sort=[("ts", -1)])
        if pcr:
            out["pcr_latest"] = pcr
    except Exception as e:
        logger.warning(f"FUND sentiment fetch failed: {e}")
        out["error"] = str(e)[:160]
    return out


# ─── Tool 4: News (BMIA news collection — symbol-filtered + recent) ────────
def fetch_news(db, symbol: str, days: int = 14, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        sym_root = symbol.upper().replace(".NS", "").replace(".BO", "")
        cursor = db.news_items.find(
            {
                "$or": [
                    {"symbols": {"$regex": sym_root, "$options": "i"}},
                    {"title": {"$regex": sym_root, "$options": "i"}},
                ],
                "published_at": {"$gte": cutoff},
            },
            {"_id": 0, "title": 1, "summary": 1, "source": 1, "published_at": 1, "url": 1, "sentiment": 1},
        ).sort("published_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.warning(f"FUND news fetch failed for {symbol}: {e}")
        return []


# ─── Tool 5: Portfolio context (for Risk Manager) ──────────────────────────
def fetch_portfolio_context(db, user_email: Optional[str] = None) -> Dict[str, Any]:
    """Best-effort portfolio summary for the user (or the default custom
    portfolio if user_email is None) so the Risk Manager can flag
    over-concentration."""
    try:
        # Custom portfolios (manual) — pull holdings + sector mix
        q = {"user_email": user_email} if user_email else {}
        positions = list(db.custom_portfolio_positions.find(q, {"_id": 0}).limit(200))
        if not positions:
            # Fall back to autonomous portfolio (latest snapshot of any strategy)
            snap = db.portfolio_snapshots.find_one({}, {"_id": 0}, sort=[("ts", -1)])
            positions = (snap or {}).get("positions", [])
        total_value = sum(float(p.get("current_value") or 0) for p in positions)
        sectors: Dict[str, float] = {}
        for p in positions:
            s = (p.get("sector") or "Unknown")[:40]
            sectors[s] = sectors.get(s, 0) + float(p.get("current_value") or 0)
        sectors = {k: round(v / total_value * 100, 1) for k, v in sectors.items()} if total_value else {}
        return {
            "ok": True,
            "n_positions": len(positions),
            "total_value": round(total_value, 0),
            "sector_mix_pct": dict(sorted(sectors.items(), key=lambda kv: -kv[1])[:8]),
            "top_5_holdings": sorted(
                [{"symbol": p.get("symbol"), "weight_pct": round(float(p.get("current_value") or 0) / total_value * 100, 1)}
                 for p in positions if total_value > 0],
                key=lambda x: -x["weight_pct"],
            )[:5],
        }
    except Exception as e:
        logger.warning(f"FUND portfolio fetch failed: {e}")
        return {"ok": False, "error": str(e)[:160]}


# ─── Tool 6: Compliance regulatory check ───────────────────────────────────
async def fetch_compliance_signal(symbol: str) -> Dict[str, Any]:
    """Quick check: is this symbol mentioned in any recent SEBI orders or NSE
    surveillance circulars? Uses the existing compliance retrieval store."""
    try:
        from services.compliance_rag import compliance_router
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        hits = compliance_router.search(
            f"{sym} order surveillance penalty",
            sources=["sebi", "nse"], top_k=5, use_embeddings=True,
        )
        relevant = [h for h in hits if sym.lower() in (h.get("title") or "").lower()
                    or sym.lower() in (h.get("text_chunk") or "").lower()[:500]]
        return {
            "ok": True,
            "regulatory_hits": [
                {"source": h.get("source"), "title": h.get("title"),
                 "date": h.get("date_iso"), "url": h.get("url"),
                 "score": round(h.get("score", 0), 3)}
                for h in relevant[:3]
            ],
            "n_hits": len(relevant),
        }
    except Exception as e:
        logger.info(f"FUND compliance signal unavailable: {e}")
        return {"ok": False, "n_hits": 0}

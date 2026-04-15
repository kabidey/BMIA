"""
Full Market Scanner — Scans ALL NSE EQ + BSE Group A stocks with multi-stage pipeline.
Stage A: Ingest full NSE bhav copy (2400+) + BSE Group A (~1000) — merged & deduped
Stage B: Quantitative pre-filter → ~50-150 candidates
Stage C: Deep feature computation → ~20-40 shortlist
Stage D: God Mode LLM ensemble → distilled BUY calls
"""
import logging
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)

# Cache for bhav copy (refreshed daily)
_bhav_cache = {"data": None, "date": None}


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        v = float(str(val).replace(",", "").replace(" ", "").strip())
        return v if not (isinstance(v, float) and v != v) else default  # NaN check
    except (ValueError, TypeError):
        return default


def get_bse_universe():
    """Fetch BSE Group A stocks for broader market coverage."""
    try:
        from services.guidance_service import get_stock_universe
        bse_stocks = get_stock_universe()
        if not bse_stocks:
            return []

        universe = []
        for stock in bse_stocks:
            sym = stock.get("symbol", "")
            if not sym:
                continue
            universe.append({
                "symbol": f"{sym}.NS",
                "ticker": sym,
                "close": None,
                "prev_close": None,
                "change_pct": 0,
                "open": None,
                "high": None,
                "low": None,
                "volume": 0,
                "traded_value": 0,
                "range_pct": 0,
                "source": "BSE",
            })
        logger.info(f"BSE universe: {len(universe)} Group A stocks")
        return universe
    except Exception as e:
        logger.warning(f"BSE universe fetch error: {e}")
        return []


def get_nse_universe(trade_date=None):
    """Stage A: Fetch ALL NSE equity stocks from bhav copy."""
    today = date.today()
    if _bhav_cache["data"] is not None and _bhav_cache["date"] == today.isoformat():
        return _bhav_cache["data"]

    from nselib import capital_market

    df = None
    for days_back in range(0, 7):
        d = today - timedelta(days=days_back)
        ds = d.strftime("%d-%m-%Y")
        try:
            df = capital_market.bhav_copy_equities(ds)
            if df is not None and len(df) > 100:
                logger.info(f"NSE bhav copy loaded for {ds}: {len(df)} rows")
                break
        except Exception as e:
            logger.debug(f"Bhav copy {ds} failed: {e}")

    if df is None or len(df) == 0:
        return []

    # Filter to equity series only
    eq = df[df["SctySrs"] == "EQ"].copy()

    universe = []
    for _, row in eq.iterrows():
        sym = str(row.get("TckrSymb", "")).strip()
        if not sym:
            continue

        close = _safe_float(row.get("ClsPric"))
        prev_close = _safe_float(row.get("PrvsClsgPric"))
        volume = _safe_float(row.get("TtlTradgVol"), 0)
        traded_value = _safe_float(row.get("TtlTrfVal"), 0)
        open_p = _safe_float(row.get("OpnPric"))
        high = _safe_float(row.get("HghPric"))
        low = _safe_float(row.get("LwPric"))

        if not close or not prev_close or close <= 0:
            continue

        change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0
        range_pct = round((high - low) / low * 100, 2) if low and high else 0

        universe.append({
            "symbol": f"{sym}.NS",
            "ticker": sym,
            "close": close,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "open": open_p,
            "high": high,
            "low": low,
            "volume": int(volume),
            "traded_value": traded_value,
            "range_pct": range_pct,
            "source": "NSE",
        })

    _bhav_cache["data"] = universe
    _bhav_cache["date"] = today.isoformat()
    logger.info(f"NSE universe: {len(universe)} EQ stocks")
    return universe


def get_combined_universe():
    """Merge NSE bhav copy + BSE Group A, deduped by ticker symbol."""
    nse = get_nse_universe()
    bse = get_bse_universe()

    # NSE data has OHLCV — it's primary. BSE fills gaps.
    seen_tickers = {s["ticker"] for s in nse}
    merged = list(nse)
    bse_added = 0
    for s in bse:
        if s["ticker"] not in seen_tickers:
            merged.append(s)
            seen_tickers.add(s["ticker"])
            bse_added += 1

    logger.info(f"Combined universe: {len(nse)} NSE + {bse_added} BSE-only = {len(merged)} total")
    return merged


def prefilter_candidates(universe, max_candidates=100):
    """
    Stage B: Quantitative pre-filter to find interesting stocks.
    We want stocks showing SIGNS of potential buy setups:
    - Strong momentum (positive change)
    - High trading activity (volume/value)
    - Range expansion (big moves)
    - Not penny stocks
    BSE-only stocks without OHLCV get a baseline score and are fetched in Stage C.
    """
    if not universe:
        return []

    nse_stocks = []
    bse_only_stocks = []

    for s in universe:
        if s.get("close") and s.get("traded_value"):
            nse_stocks.append(s)
        else:
            bse_only_stocks.append(s)

    # Basic liquidity filter for NSE stocks: traded value > 50 lakhs, price > 10
    liquid = [s for s in nse_stocks if s["traded_value"] > 5_000_000 and s["close"] > 10]
    logger.info(f"After liquidity filter: {len(liquid)} NSE stocks (from {len(nse_stocks)}), {len(bse_only_stocks)} BSE-only")

    # Score each NSE stock
    for s in liquid:
        score = 0.0
        if s["change_pct"] > 0:
            score += min(s["change_pct"] * 2, 15)
        elif s["change_pct"] < -3:
            score += 3
        if s["range_pct"] > 3:
            score += min(s["range_pct"], 10)
        if s["traded_value"] > 1e9:
            score += 8
        elif s["traded_value"] > 5e8:
            score += 5
        elif s["traded_value"] > 1e8:
            score += 3
        if s["high"] and s["low"] and s["high"] != s["low"]:
            close_position = (s["close"] - s["low"]) / (s["high"] - s["low"])
            if close_position > 0.7:
                score += 5
        s["prefilter_score"] = round(score, 2)

    # Sort NSE by score
    liquid.sort(key=lambda x: x["prefilter_score"], reverse=True)

    # Take top NSE candidates + a few BSE-only (which will be evaluated in Stage C)
    bse_slots = max(max_candidates // 5, 5)
    candidates = liquid[:max_candidates - bse_slots]

    # Add BSE-only stocks (random sample — they'll get real data in Stage C)
    import random
    bse_sample = random.sample(bse_only_stocks, min(bse_slots, len(bse_only_stocks))) if bse_only_stocks else []
    for s in bse_sample:
        s["prefilter_score"] = 5.0  # baseline
    candidates.extend(bse_sample)

    logger.info(f"Pre-filter: {len(candidates)} candidates ({len(candidates) - len(bse_sample)} NSE + {len(bse_sample)} BSE-only)")
    return candidates


def build_shortlist(candidates, max_shortlist=20):
    """
    Stage C: Deep feature computation on candidates.
    Fetch yfinance data and compute expanded technicals for the shortlist.
    HARDENED: Per-stock timeout (8s), data sanitization, factor scoring.
    """
    import concurrent.futures
    from services.technical_service import full_technical_analysis
    from services.fundamental_service import get_fundamentals
    from services.portfolio_hardening import validate_fundamentals, validate_technical

    def _fetch_one(c):
        """Fetch and compute features for a single candidate (runs in thread)."""
        sym = c["symbol"]
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="3mo")
            if hist is None or len(hist) < 20:
                return None

            # Build OHLCV data
            ohlcv = []
            for ts, row in hist.iterrows():
                ohlcv.append({
                    "time": ts.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })

            # Compute technicals + sanitize
            technical = full_technical_analysis(ohlcv)
            technical = validate_technical(technical) if isinstance(technical, dict) else {}

            # Get fundamentals + sanitize
            fundamentals = get_fundamentals(sym)
            fundamentals = validate_fundamentals(fundamentals) if isinstance(fundamentals, dict) else {}

            # Calculate volume ratio (today vs 10d avg)
            if len(hist) >= 11:
                current_vol = float(hist["Volume"].iloc[-1])
                avg_vol_10d = float(hist["Volume"].iloc[-11:-1].mean())
                vol_ratio = round(current_vol / max(avg_vol_10d, 1), 1)
            else:
                vol_ratio = 1.0

            return {
                "symbol": sym,
                "name": c["ticker"],
                "sector": fundamentals.get("sector", "N/A") if isinstance(fundamentals, dict) else "N/A",
                "market_data": {
                    "price": c["close"],
                    "change": round(c["close"] - c["prev_close"], 2),
                    "change_pct": c["change_pct"],
                    "volume": c["volume"],
                    "vol_ratio": vol_ratio,
                },
                "technical": technical,
                "fundamental": fundamentals,
                "prefilter_score": c["prefilter_score"],
            }
        except Exception as e:
            logger.debug(f"Shortlist skip {sym}: {e}")
            return None

    # Use ThreadPoolExecutor with per-stock timeout
    shortlist = []
    batch = candidates[:max_shortlist * 2]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(_fetch_one, c): c for c in batch}
        for future in concurrent.futures.as_completed(future_map, timeout=90):
            try:
                result = future.result(timeout=8)
                if result:
                    shortlist.append(result)
                    if len(shortlist) >= max_shortlist:
                        break
            except (concurrent.futures.TimeoutError, Exception) as e:
                sym = future_map[future].get("symbol", "?")
                logger.debug(f"Shortlist timeout/error {sym}: {e}")

    logger.info(f"Shortlist: {len(shortlist)} stocks with full data (hardened)")
    return shortlist


async def god_mode_scan(market="NSE", max_candidates=80, max_shortlist=15, top_n=15):
    """
    Full pipeline: Universe → Prefilter → Shortlist → God Mode → Ranked BUY calls.
    HARDENED: 3-minute hard cap, sanitized data, factor scores attached.
    Scans both NSE (2400+) and BSE Group A (~1000) stocks merged & deduped.
    """
    import asyncio
    from services.intelligence_engine import generate_god_mode_batch_ranking
    from services.portfolio_hardening import compute_factor_score

    pipeline_status = {
        "stage": "universe",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    # Stage A: Combined Universe (NSE + BSE)
    logger.info("GOD SCAN Stage A: Loading NSE + BSE universe...")
    universe = get_combined_universe()
    pipeline_status["universe_size"] = len(universe)
    pipeline_status["nse_count"] = sum(1 for s in universe if s.get("source") == "NSE")
    pipeline_status["bse_only_count"] = sum(1 for s in universe if s.get("source") == "BSE")

    if not universe:
        # Retry with just NSE
        logger.warning("GOD SCAN: Combined universe empty, retrying NSE only...")
        universe = get_nse_universe()
        pipeline_status["universe_size"] = len(universe)
        pipeline_status["retry"] = "nse_only"

    if not universe:
        return {"error": "Failed to load universe from both NSE and BSE. Market may be closed.", "pipeline": pipeline_status}

    # Stage B: Prefilter
    logger.info("GOD SCAN Stage B: Pre-filtering...")
    pipeline_status["stage"] = "prefilter"
    candidates = prefilter_candidates(universe, max_candidates=max_candidates)
    pipeline_status["candidates"] = len(candidates)

    if not candidates:
        return {"error": "No candidates after prefilter", "pipeline": pipeline_status}

    # Stage C: Deep features (hardened with timeouts)
    logger.info("GOD SCAN Stage C: Building shortlist with deep features...")
    pipeline_status["stage"] = "shortlist"
    shortlist = build_shortlist(candidates, max_shortlist=max_shortlist)
    pipeline_status["shortlist_size"] = len(shortlist)

    if not shortlist:
        return {"error": "No stocks in shortlist after feature computation", "pipeline": pipeline_status}

    # Attach factor scores to shortlist
    for s in shortlist:
        try:
            score = compute_factor_score(s, "alpha_generator")
            s["factor_score"] = score
        except Exception:
            s["factor_score"] = None

    # Stage D: God Mode ensemble (with 180s hard timeout)
    logger.info(f"GOD SCAN Stage D: God Mode ensemble on {len(shortlist)} stocks...")
    pipeline_status["stage"] = "god_mode"
    try:
        ranking_result = await asyncio.wait_for(
            generate_god_mode_batch_ranking(shortlist),
            timeout=180,
        )
    except asyncio.TimeoutError:
        logger.error("GOD SCAN Stage D: LLM ensemble timed out after 180s")
        ranking_result = {"error": "LLM ensemble timed out. Try again."}

    pipeline_status["stage"] = "complete"
    pipeline_status["completed_at"] = datetime.now(timezone.utc).isoformat()

    if "error" in ranking_result:
        # Fallback: return shortlist sorted by factor score
        fallback = sorted(shortlist, key=lambda x: x.get("factor_score") or 0, reverse=True)
        return {
            "results": [{
                "symbol": s["symbol"],
                "name": s["name"],
                "sector": s["sector"],
                "price": s["market_data"]["price"],
                "change_pct": s["market_data"]["change_pct"],
                "volume": s["market_data"]["volume"],
                "vol_ratio": s["market_data"]["vol_ratio"],
                "rsi": s["technical"].get("rsi", {}).get("current"),
                "prefilter_score": s["prefilter_score"],
                "factor_score": s.get("factor_score"),
                "ai_score": None,
                "action": "N/A",
                "conviction": "N/A",
                "agreement_level": "N/A",
                "rationale": f"God Mode failed: {ranking_result['error']}",
                "model_votes": {},
                "rank": i + 1,
            } for i, s in enumerate(fallback)],
            "total": len(fallback),
            "god_mode": False,
            "pipeline": pipeline_status,
            "error": ranking_result.get("error"),
        }

    # Merge rankings with market data
    rankings = ranking_result.get("rankings", [])
    ranking_map = {r.get("symbol", ""): r for r in rankings}

    results = []
    for s in shortlist:
        ai = ranking_map.get(s["symbol"], ranking_map.get(s["name"], {}))
        results.append({
            "symbol": s["symbol"],
            "name": s["name"],
            "sector": s["sector"],
            "price": s["market_data"]["price"],
            "change_pct": s["market_data"]["change_pct"],
            "volume": s["market_data"]["volume"],
            "vol_ratio": s["market_data"]["vol_ratio"],
            "rsi": s["technical"].get("rsi", {}).get("current"),
            "macd_signal": s["technical"].get("macd", {}).get("crossover"),
            "adx": s["technical"].get("adx", {}).get("adx"),
            "bollinger_squeeze": s["technical"].get("bollinger", {}).get("squeeze"),
            "pe_ratio": s["fundamental"].get("pe_ratio"),
            "roe": s["fundamental"].get("roe"),
            "prefilter_score": s["prefilter_score"],
            "factor_score": s.get("factor_score"),
            "rank": ai.get("rank", 99),
            "ai_score": ai.get("ai_score"),
            "action": ai.get("action", "N/A"),
            "conviction": ai.get("conviction", "N/A"),
            "agreement_level": ai.get("agreement_level", "N/A"),
            "rationale": ai.get("rationale", ""),
            "key_strength": ai.get("key_strength", ""),
            "key_risk": ai.get("key_risk", ""),
            "model_votes": ai.get("model_votes", {}),
        })

    results.sort(key=lambda x: x.get("rank", 99))

    return {
        "results": results[:top_n],
        "total": len(results),
        "god_mode": ranking_result.get("god_mode", True),
        "models_succeeded": ranking_result.get("models_succeeded", []),
        "generated_at": ranking_result.get("generated_at"),
        "pipeline": pipeline_status,
    }

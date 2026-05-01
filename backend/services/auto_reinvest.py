"""
Strategy-aware PMS-style auto-reinvestment.

When any position exits (stop-loss / take-profit / rebalance), pick a
replacement stock that fits the PORTFOLIO'S OWN INVESTMENT THESIS —
not a generic momentum pick. Reuses the existing strategy config
(PORTFOLIO_STRATEGIES) so each portfolio stays true to its mandate:

  momentum / breakout → recent upside, volume, trend
  blue_chip          → large cap, stable, low volatility, low DE
  oversold           → recent drawdown + RSI low + mean reversion setup
  contrarian / value → low PE, high ROE, margin of safety
"""
import logging
import time
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

# Fallback universe if bhav copy is unavailable (NIFTY-200 heavyweights)
FALLBACK_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "AXISBANK.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "SUNPHARMA.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS",
    "ADANIENT.NS", "M&M.NS", "NESTLEIND.NS", "POWERGRID.NS",
    "NTPC.NS", "TATASTEEL.NS", "ONGC.NS", "TECHM.NS", "JSWSTEEL.NS",
    "COALINDIA.NS", "HINDALCO.NS", "BAJAJFINSV.NS", "GRASIM.NS", "HDFCLIFE.NS",
    "ADANIPORTS.NS", "CIPLA.NS", "DRREDDY.NS", "EICHERMOT.NS", "DIVISLAB.NS",
    "BRITANNIA.NS", "HEROMOTOCO.NS", "DMART.NS", "SBILIFE.NS", "APOLLOHOSP.NS",
    "BPCL.NS", "INDUSINDBK.NS", "BAJAJ-AUTO.NS", "SHREECEM.NS", "PIDILITIND.NS",
    "TATACONSUM.NS", "VEDL.NS", "GODREJCP.NS", "SIEMENS.NS", "BOSCHLTD.NS",
    "LTIM.NS", "CHOLAFIN.NS", "HAVELLS.NS", "DABUR.NS", "AMBUJACEM.NS",
    "TRENT.NS", "BEL.NS", "ICICIPRULI.NS", "TATAPOWER.NS", "GAIL.NS",
    "IOC.NS", "HAL.NS", "JINDALSTEL.NS", "MUTHOOTFIN.NS", "NAUKRI.NS",
    "IRCTC.NS", "LUPIN.NS", "BIOCON.NS", "TVSMOTOR.NS", "SRF.NS",
    "BANDHANBNK.NS", "HINDPETRO.NS", "PERSISTENT.NS", "MPHASIS.NS", "COFORGE.NS",
]


def _get_universe(strategy_type: str, min_price: float = 50, min_traded_value: float = 1e7) -> list:
    """Build replenishment universe from daily bhav copy (top-liquid N stocks).

    For small/mid-cap-friendly strategies (swing, value_stocks, alpha_generator,
    quick_entry) we take top 400 by traded value → NIFTY-500 equivalent breadth.
    For blue_chip / momentum strategies we stick to top 150 (large-mid cap).
    Falls back to a hardcoded NIFTY-200 list if bhav copy is unavailable.
    """
    try:
        from services.full_market_scanner import get_nse_universe
        nse = get_nse_universe()
        if not nse:
            return FALLBACK_UNIVERSE

        # Basic liquidity + price gate
        liquid = [
            s for s in nse
            if s.get("close", 0) >= min_price
            and s.get("traded_value", 0) >= min_traded_value
        ]
        # Rank by traded value descending
        liquid.sort(key=lambda x: x.get("traded_value", 0), reverse=True)

        # Strategy-appropriate breadth
        broad_caps = {"swing", "value_stocks", "alpha_generator", "quick_entry"}
        top_n = 400 if strategy_type in broad_caps else 150

        symbols = [s["symbol"] for s in liquid[:top_n]]
        logger.info(f"REPLENISH_UNIVERSE [{strategy_type}]: {len(symbols)} liquid stocks from bhav copy")
        return symbols
    except Exception as e:
        logger.warning(f"Bhav copy universe fetch failed ({e}), using fallback NIFTY-200")
        return FALLBACK_UNIVERSE


def _fetch_candidate_data(symbol: str) -> Optional[dict]:
    """Fetch price history + fundamentals for scoring."""
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period="6mo")
        if hist is None or len(hist) < 60:
            return None
        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]
        volume = hist["Volume"]

        current = float(close.iloc[-1])
        p_1m = float(close.iloc[-21]) if len(close) >= 21 else float(close.iloc[0])
        p_3m = float(close.iloc[-63]) if len(close) >= 63 else float(close.iloc[0])
        p_6m = float(close.iloc[0])
        high_6m = float(high.max())
        low_6m = float(low.min())

        # RSI-14 (simplified)
        delta = close.diff().dropna()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] > 0 else 100
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

        # Volatility (stdev of daily returns × sqrt(252))
        daily_ret = close.pct_change().dropna()
        vol = float(daily_ret.std() * (252 ** 0.5) * 100) if len(daily_ret) > 0 else 0

        # Avg daily traded value
        avg_tv = float((close * volume).mean())

        info = tk.info or {}

        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol.replace(".NS", ""),
            "sector": info.get("sector", "N/A"),
            "current_price": round(current, 2),
            "ret_1m_pct": round((current - p_1m) / p_1m * 100, 2) if p_1m > 0 else 0,
            "ret_3m_pct": round((current - p_3m) / p_3m * 100, 2) if p_3m > 0 else 0,
            "ret_6m_pct": round((current - p_6m) / p_6m * 100, 2) if p_6m > 0 else 0,
            "dist_from_high_pct": round((high_6m - current) / high_6m * 100, 2) if high_6m > 0 else 0,
            "dist_from_low_pct": round((current - low_6m) / low_6m * 100, 2) if low_6m > 0 else 0,
            "rsi": round(float(rsi), 1),
            "volatility_ann_pct": round(vol, 2),
            "avg_traded_value": avg_tv,
            # Fundamentals
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
        }
    except Exception as e:
        logger.debug(f"Candidate fetch failed for {symbol}: {e}")
        return None


def _passes_screener(c: dict, criteria: dict) -> bool:
    """Apply a strategy's screener_criteria fundamental gates."""
    mc = c.get("market_cap")
    if criteria.get("market_cap_min") and (mc is None or mc < criteria["market_cap_min"]):
        return False
    if "pe_max" in criteria:
        pe = c.get("pe_ratio")
        if pe is not None and pe > criteria["pe_max"]:
            return False
    if "price_to_book_max" in criteria:
        pb = c.get("price_to_book")
        if pb is not None and pb > criteria["price_to_book_max"]:
            return False
    if "roe_min" in criteria:
        roe = c.get("roe")
        if roe is not None and roe < criteria["roe_min"] / 100:
            return False
    if "debt_to_equity_max" in criteria:
        de = c.get("debt_to_equity")
        if de is not None and de > criteria["debt_to_equity_max"] * 100:
            return False
    if "revenue_growth_min" in criteria:
        rg = c.get("revenue_growth")
        if rg is not None and rg < criteria["revenue_growth_min"] / 100:
            return False
    if "profit_margin_min" in criteria:
        pm = c.get("profit_margin")
        if pm is not None and pm < criteria["profit_margin_min"] / 100:
            return False
    return True


def _score_by_strategy(c: dict, scoring: str) -> float:
    """Strategy-specific composite score. Higher = better fit for thesis."""
    score = 0.0
    r1, r3, r6 = c["ret_1m_pct"], c["ret_3m_pct"], c["ret_6m_pct"]
    rsi = c["rsi"]
    dist_hi, dist_lo = c["dist_from_high_pct"], c["dist_from_low_pct"]
    vol = c["volatility_ann_pct"]
    mc = c.get("market_cap") or 0
    pe = c.get("pe_ratio")
    pb = c.get("price_to_book")
    roe = c.get("roe") or 0
    pm = c.get("profit_margin") or 0
    dy = c.get("dividend_yield") or 0
    rg = c.get("revenue_growth") or 0
    de = c.get("debt_to_equity") or 0
    beta = c.get("beta")

    if scoring == "momentum":
        # Bespoke Forward Looking — reward recent 3M momentum, penalize overbought
        score += r3 * 0.6 + r6 * 0.2 + r1 * 0.2
        if r3 > 40:  # probable blow-off top
            score *= 0.4
        if 40 <= rsi <= 70:
            score += 5
        if rg > 0.10:
            score += 8

    elif scoring == "breakout":
        # Quick Entry — near-term breakout + strong recent move
        score += r1 * 0.7 + r3 * 0.3
        if r1 > 5 and rsi < 75:
            score += 10  # breakout not yet exhausted
        if dist_hi < 5:
            score += 8  # near 6M high = breakout zone
        if r1 > 15:  # too fast
            score *= 0.5

    elif scoring == "blue_chip":
        # Long Term Compounder — stability, quality, size
        if mc > 50000e7:
            score += 15
        elif mc > 20000e7:
            score += 10
        if vol < 25:
            score += 10  # low vol preferred
        if roe > 0.15:
            score += 10
        if pm > 0.10:
            score += 5
        if de < 100:
            score += 5
        # Reward positive but not crazy returns
        if 0 < r6 < 30:
            score += r6 * 0.3
        if beta and 0.6 < beta < 1.2:
            score += 3

    elif scoring == "oversold":
        # Swing Trader — mean reversion from recent lows
        if rsi < 40:
            score += (40 - rsi) * 0.8
        if r1 < -3:
            score += min(abs(r1) * 1.5, 12)  # recent drawdown
        if dist_lo < 10:
            score += 8  # near 6M low
        if 0 < r6 < 25:  # longer-term uptrend intact
            score += 5

    elif scoring == "contrarian":
        # Alpha Generator — undervalued + recent underperformance
        if pe is not None and 0 < pe < 20:
            score += (20 - pe) * 0.8
        if r1 < 0 and r6 > 0:
            score += 10  # recent dip in uptrend
        if roe > 0.12:
            score += 8
        if dy > 0.015:
            score += 5
        if mc > 2000e7 and vol < 35:
            score += 5

    elif scoring == "value":
        # Value Stocks — deep value (low PE, low PB, healthy ROE, high DY)
        if pe is not None and 0 < pe < 15:
            score += (15 - pe) * 1.2
        if pb is not None and 0 < pb < 2.5:
            score += (2.5 - pb) * 5
        if roe > 0.12:
            score += 10
        if de < 50:
            score += 5
        # dividend_yield may arrive as fraction (0.023) or pct (2.3) from yfinance
        dy_frac = dy / 100 if dy > 1 else dy
        if dy_frac > 0.02:
            score += min(dy_frac * 500, 15)  # cap DY contribution at 15 points

    else:  # fallback: simple momentum
        score += r3 * 0.7 + r6 * 0.3

    return round(score, 2)


def pick_replacement_stock(
    held_symbols: set,
    cash_available: float,
    strategy_type: str = None,
    max_candidates: int = 40,
) -> Optional[dict]:
    """Pick best replacement stock respecting the portfolio's own thesis.

    Args:
      held_symbols: set of symbols already held (exclude)
      cash_available: cash budget for the buy
      strategy_type: key into PORTFOLIO_STRATEGIES; if None, fallback to momentum
      max_candidates: universe size to score

    Returns:
      {symbol, name, sector, current_price, quantity, score, ...} or None
    """
    if cash_available <= 0:
        return None

    # Lazy import to avoid circular deps
    from services.portfolio_engine import PORTFOLIO_STRATEGIES
    cfg = PORTFOLIO_STRATEGIES.get(strategy_type) if strategy_type else None
    scoring = (cfg or {}).get("scoring", "momentum")
    criteria = (cfg or {}).get("screener_criteria", {})
    min_price = (cfg or {}).get("min_price", 50)
    min_tv = (cfg or {}).get("min_traded_value", 1e7)

    # Build liquid universe from bhav copy (strategy-appropriate breadth)
    full_universe = _get_universe(strategy_type, min_price=min_price, min_traded_value=min_tv)

    # Exclude already-held
    available = [s for s in full_universe if s not in held_symbols]

    # Strategy-aware sampling: broad strategies get a diversified sample
    # across the liquidity spectrum (not just the most liquid mega-caps);
    # narrow strategies stick to the top of the list.
    broad_caps = {"swing", "value_stocks", "alpha_generator", "quick_entry"}
    if strategy_type in broad_caps and len(available) > max_candidates:
        # Stride sampling across the full list to capture mid-caps
        stride = max(1, len(available) // max_candidates)
        universe = available[::stride][:max_candidates]
    else:
        universe = available[:max_candidates]

    scored = []
    for sym in universe:
        c = _fetch_candidate_data(sym)
        if not c or c["current_price"] <= 0:
            continue
        if not _passes_screener(c, criteria):
            continue
        c["score"] = _score_by_strategy(c, scoring)
        c["strategy_fit"] = scoring
        scored.append(c)
        time.sleep(0.15)

    if not scored:
        logger.warning(f"REINVEST [{strategy_type}]: No candidates passed screener {criteria}")
        return None

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Pick top that fits budget
    for cand in scored[:10]:
        qty = int(cash_available / cand["current_price"])
        if qty >= 1:
            cand["quantity"] = qty
            cand["deployed"] = round(qty * cand["current_price"], 2)
            return cand
    return None


def reinvest_proceeds(db, portfolio_type: str, proceeds: float, source_exit: dict) -> Optional[dict]:
    """Deploy cash proceeds from an exit into a strategy-appropriate stock."""
    if proceeds <= 0:
        return None

    # Hard rule: auto-reinvest only during safe market hours
    from utils.market_hours import is_market_safe_sync
    ok, reason = is_market_safe_sync(db)
    if not ok:
        logger.info(f"REINVEST [{portfolio_type}]: skipped — {reason}")
        return None

    p = db.portfolios.find_one({"type": portfolio_type})
    if not p:
        return None

    held = {h["symbol"] for h in p.get("holdings", [])}
    replacement = pick_replacement_stock(held, proceeds, strategy_type=portfolio_type)
    if not replacement:
        logger.warning(f"REINVEST [{portfolio_type}]: No viable replacement for ₹{proceeds:,.0f}")
        return None

    freed_weight = source_exit.get("weight", 0) or (
        sum(h.get("weight", 0) for h in p.get("holdings", [])) / max(len(p.get("holdings", [])), 1)
    )

    from datetime import datetime
    thesis_tag = replacement.get("strategy_fit", "momentum").upper()
    rationale = (
        f"Auto-redeployed from {source_exit.get('symbol','exit')} proceeds using "
        f"{thesis_tag} strategy filter. "
        f"Score {replacement['score']} | 1M {replacement['ret_1m_pct']}% | "
        f"3M {replacement['ret_3m_pct']}% | RSI {replacement['rsi']} | "
        f"MC ₹{(replacement.get('market_cap') or 0)/1e7:.0f}Cr"
    )

    new_holding = {
        "symbol": replacement["symbol"],
        "name": replacement["name"],
        "sector": replacement["sector"],
        "entry_price": replacement["current_price"],
        "current_price": replacement["current_price"],
        "quantity": replacement["quantity"],
        "weight": round(freed_weight, 1),
        "allocation": replacement["deployed"],
        "pnl": 0,
        "pnl_pct": 0,
        "conviction": "AUTO_REINVEST",
        "rationale": rationale,
        "key_catalyst": f"Strategy-aware replenishment ({thesis_tag})",
        "risk_flag": "",
        "entry_date": datetime.now().isoformat(),
    }

    holdings = p.get("holdings", []) + [new_holding]
    # ─── BUG FIX (2026-04): Double-booking guard ────────────────────────────
    # `_enforce_stops` (and `_execute_rebalance`) ALREADY bank `proceeds` into
    # `cash_balance` BEFORE calling us. Adding `proceeds` again here was
    # double-counting — inflating cash, NAV, and total_pnl by exactly the
    # exit proceeds. Treat the on-disk `cash_balance` as authoritative and
    # only deduct what we just deployed.
    current_cash = float(p.get("cash_balance", 0) or 0)
    cash_balance = current_cash - replacement["deployed"]

    db.portfolios.update_one(
        {"type": portfolio_type},
        {"$set": {
            "holdings": holdings,
            "cash_balance": round(cash_balance, 2),
        }}
    )

    logger.info(
        f"REINVEST [{portfolio_type}/{thesis_tag}]: "
        f"{source_exit.get('symbol','?')} → {replacement['symbol']} "
        f"qty={replacement['quantity']} @ ₹{replacement['current_price']} "
        f"= ₹{replacement['deployed']:,.0f} (score={replacement['score']})"
    )

    return {**replacement, "freed_weight": round(freed_weight, 2), "new_holding": new_holding}

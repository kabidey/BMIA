"""
PMS-style auto-reinvestment: after any exit (stop-loss, take-profit, or
rebalance), immediately deploy the cash proceeds into a replacement stock
so that portfolio NAV = Holdings MV + Cash, with cash always ~0.

Uses a fast factor-based shortlist (momentum-weighted) from the strategy's
own universe — no LLM call. Matches the existing hardened shortlist's
universe rules.
"""
import logging
import time
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

# Large-mid-cap universe (NIFTY 200 tickers) — liquid, reliable for any strategy
REPLENISH_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "AXISBANK.NS", "MARUTI.NS",
    "ASIANPAINT.NS", "SUNPHARMA.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS",
    "TATAMOTORS.NS", "ADANIENT.NS", "M&M.NS", "NESTLEIND.NS", "POWERGRID.NS",
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


def _score_candidate(symbol: str) -> Optional[dict]:
    """Momentum-biased score: 3M return weighted by 6M trend.
    Returns {symbol, score, current_price, name, sector} or None.
    """
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period="6mo")
        if hist is None or len(hist) < 60:
            return None
        close = hist["Close"]
        current = float(close.iloc[-1])
        p_3m = float(close.iloc[-63]) if len(close) >= 63 else float(close.iloc[0])
        p_6m = float(close.iloc[0])
        if p_3m <= 0 or p_6m <= 0:
            return None
        ret_3m = (current - p_3m) / p_3m * 100
        ret_6m = (current - p_6m) / p_6m * 100
        # Momentum score: weight recent 3M more
        score = ret_3m * 0.7 + ret_6m * 0.3
        # Penalize overbought (recent >30% moves are often reversals)
        if ret_3m > 35:
            score *= 0.5

        info = tk.info or {}
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol.replace(".NS", ""),
            "sector": info.get("sector", "N/A"),
            "current_price": round(current, 2),
            "score": round(score, 2),
            "ret_3m_pct": round(ret_3m, 2),
            "ret_6m_pct": round(ret_6m, 2),
        }
    except Exception as e:
        logger.debug(f"Score failed for {symbol}: {e}")
        return None


def pick_replacement_stock(held_symbols: set, cash_available: float, max_candidates: int = 40) -> Optional[dict]:
    """Pick the best momentum-ranked replacement stock not currently held.

    Args:
      held_symbols: set of symbols already in portfolio (to exclude)
      cash_available: cash budget for the buy
      max_candidates: universe size to score

    Returns:
      Picked stock dict with {symbol, name, sector, current_price, quantity} or None.
    """
    if cash_available <= 0:
        return None

    # Sample from universe (skip held)
    universe = [s for s in REPLENISH_UNIVERSE if s not in held_symbols][:max_candidates]
    scored = []
    for sym in universe:
        sc = _score_candidate(sym)
        if sc and sc["current_price"] > 0:
            scored.append(sc)
        time.sleep(0.15)

    if not scored:
        return None

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Pick top — must fit within budget (at least 1 share)
    for cand in scored[:10]:
        qty = int(cash_available / cand["current_price"])
        if qty >= 1:
            cand["quantity"] = qty
            cand["deployed"] = round(qty * cand["current_price"], 2)
            return cand

    return None


def reinvest_proceeds(db, portfolio_type: str, proceeds: float, source_exit: dict) -> Optional[dict]:
    """Deploy cash proceeds from an exit into a replacement stock.

    Args:
      db: sync Mongo db
      portfolio_type: strategy name
      proceeds: amount of cash to deploy
      source_exit: dict describing the exit (for logging)

    Returns:
      dict with replacement stock info, or None if no replacement could be picked.
    """
    if proceeds <= 0:
        return None

    p = db.portfolios.find_one({"type": portfolio_type})
    if not p:
        return None

    held = {h["symbol"] for h in p.get("holdings", [])}
    replacement = pick_replacement_stock(held, proceeds)
    if not replacement:
        logger.warning(f"REINVEST [{portfolio_type}]: No viable replacement found for ₹{proceeds:,.0f}")
        return None

    # Compute weight — freed weight from exit, or average of existing holdings
    freed_weight = source_exit.get("weight", 0) or (
        sum(h.get("weight", 0) for h in p.get("holdings", [])) / max(len(p.get("holdings", [])), 1)
    )

    from datetime import datetime
    now = datetime.now().isoformat()
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
        "rationale": f"Auto-redeployed from {source_exit.get('symbol','exit')} proceeds. "
                     f"Momentum score {replacement['score']} (3M {replacement['ret_3m_pct']}%, 6M {replacement['ret_6m_pct']}%).",
        "key_catalyst": "Automated replenishment",
        "risk_flag": "",
        "entry_date": now,
    }

    # Add to holdings, reduce cash_balance by the deployed amount
    holdings = p.get("holdings", []) + [new_holding]
    cash_balance = float(p.get("cash_balance", 0) or 0) + proceeds - replacement["deployed"]

    db.portfolios.update_one(
        {"type": portfolio_type},
        {"$set": {
            "holdings": holdings,
            "cash_balance": round(cash_balance, 2),
        }}
    )

    logger.info(
        f"REINVEST [{portfolio_type}]: {source_exit.get('symbol','?')} → {replacement['symbol']} "
        f"qty={replacement['quantity']} @ ₹{replacement['current_price']} = ₹{replacement['deployed']:,.0f}"
    )

    return {
        **replacement,
        "freed_weight": round(freed_weight, 2),
        "new_holding": new_holding,
    }

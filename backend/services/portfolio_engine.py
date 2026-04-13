"""
Portfolio Engine — Autonomous AI-managed portfolios using God Mode (3-LLM consensus).

6 Strategy Portfolios, each ₹50 lakhs:
  1. Bespoke Forward Looking — Future catalysts, sector tailwinds (6-12 mo)
  2. Quick Entry — Momentum breakouts, volume spikes (1-4 weeks)
  3. Long Term — Blue-chip compounders, moat businesses (2-5 years)
  4. Swing — Technical mean reversion, RSI oversold (1-2 weeks)
  5. Alpha Generator — Contrarian, mispriced, insider buying
  6. Value Stocks — Deep value, low P/E, high dividend, Buffett-style

Fully autonomous: constructs, monitors, rebalances without human intervention.
"""
import os
import json
import re
import logging
import time
import threading
from datetime import datetime, date, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

INITIAL_CAPITAL = 5_000_000  # ₹50 lakhs per portfolio

PORTFOLIO_STRATEGIES = {
    "bespoke_forward_looking": {
        "name": "Bespoke Forward Looking",
        "description": "Stocks with strong future catalysts — upcoming product launches, market expansion, policy tailwinds. 6-12 month horizon.",
        "horizon": "6-12 months",
        "min_price": 100,
        "min_traded_value": 5e7,
        "scoring": "momentum",
    },
    "quick_entry": {
        "name": "Quick Entry",
        "description": "Momentum plays — breakout from consolidation, volume spikes, immediate upside. 1-4 week horizon.",
        "horizon": "1-4 weeks",
        "min_price": 50,
        "min_traded_value": 2e7,
        "scoring": "breakout",
    },
    "long_term": {
        "name": "Long Term Compounder",
        "description": "Blue-chip compounders — consistent earnings, strong moat, market leaders. 2-5 year horizon.",
        "horizon": "2-5 years",
        "min_price": 200,
        "min_traded_value": 1e8,
        "scoring": "blue_chip",
    },
    "swing": {
        "name": "Swing Trader",
        "description": "Technical swing trades — stocks at support, RSI oversold, mean reversion setups. 1-2 week horizon.",
        "horizon": "1-2 weeks",
        "min_price": 50,
        "min_traded_value": 2e7,
        "scoring": "oversold",
    },
    "alpha_generator": {
        "name": "Alpha Generator",
        "description": "High-conviction contrarian picks — undervalued, mispriced by market, strong insider buying. Beat the market.",
        "horizon": "3-6 months",
        "min_price": 50,
        "min_traded_value": 5e7,
        "scoring": "contrarian",
    },
    "value_stocks": {
        "name": "Value Stocks",
        "description": "Deep value — low P/E, high dividend yield, strong book value, margin of safety. Warren Buffett style.",
        "horizon": "1-3 years",
        "min_price": 50,
        "min_traded_value": 5e7,
        "scoring": "value",
    },
}

PORTFOLIO_CONSTRUCTION_PROMPT = """You are the Bharat Market Intel Agent (BMIA) — Autonomous Portfolio Construction Engine.

STRATEGY: {strategy_name}
DESCRIPTION: {strategy_description}
INVESTMENT HORIZON: {horizon}
CAPITAL: ₹50,00,000 (50 lakhs)

You are constructing a portfolio from the Indian equity market. You must select EXACTLY 10 stocks
from the shortlisted candidates below. For each stock, assign a weight (percentage of capital).

CRITICAL RULES:
1. Select EXACTLY 10 stocks. No more, no less.
2. Weights MUST sum to exactly 100%.
3. Minimum weight per stock: 5%. Maximum: 20%.
4. Every pick must align with the strategy description above.
5. Diversify across sectors — no more than 3 stocks from the same sector.
6. A BAD STOCK PICK IS AN AI DISCREDIT. Think 100 times before selecting.
7. Only reference data from the provided context. Never fabricate.
8. Entry price must be the current market price (close price provided).
9. Provide detailed rationale for EACH selection citing specific metrics.

Return ONLY valid JSON:
{{
  "selections": [
    {{
      "symbol": "<SYMBOL.NS>",
      "name": "<company name>",
      "weight": <float 5-20>,
      "entry_price": <float current close>,
      "rationale": "<detailed 2-3 sentence rationale citing specific technical/fundamental metrics>",
      "conviction": "HIGH" | "MEDIUM",
      "sector": "<sector name>",
      "key_catalyst": "<single most important catalyst for this strategy>"
    }}
  ],
  "portfolio_thesis": "<2-3 sentence overall thesis for this portfolio>",
  "risk_assessment": "<key risks to watch>"
}}"""

PORTFOLIO_REBALANCE_PROMPT = """You are the Bharat Market Intel Agent (BMIA) — Autonomous Portfolio Rebalancing Engine.

STRATEGY: {strategy_name}
DESCRIPTION: {strategy_description}
INVESTMENT HORIZON: {horizon}

CURRENT PORTFOLIO (constructed {days_since} days ago):
{current_holdings}

PORTFOLIO PERFORMANCE:
- Initial Capital: ₹50,00,000
- Current Value: ₹{current_value}
- Total P&L: {total_pnl} ({total_pnl_pct}%)
- Winners: {winners} | Losers: {losers}

MARKET CANDIDATES (potential replacements):
{market_candidates}

CRITICAL RULES:
1. A BAD STOCK PICK IS AN AI DISCREDIT. Think 100 times before recommending ANY change.
2. DO NOT recommend changes just for the sake of activity. If the portfolio is performing well, say "NO_CHANGE".
3. Only recommend replacing a stock if:
   - It has fundamentally deteriorated (broken thesis)
   - A significantly better opportunity exists
   - The stock has hit its target and momentum is fading
   - Stop-loss has been breached
4. Maximum 2 replacements per rebalancing cycle.
5. For every outgoing stock, explain WHY it must go with specific data.
6. For every incoming stock, explain WHY it's better with specific data.
7. Preserve portfolio diversification — don't concentrate in one sector.

Return ONLY valid JSON:
{{
  "action": "REBALANCE" | "NO_CHANGE",
  "analysis_summary": "<2-3 paragraph analysis of current portfolio health>",
  "confidence": <int 0-100>,
  "changes": [
    {{
      "outgoing": {{
        "symbol": "<symbol to remove>",
        "rationale": "<detailed reason for removal citing metrics>"
      }},
      "incoming": {{
        "symbol": "<SYMBOL.NS>",
        "name": "<company name>",
        "weight": <float>,
        "entry_price": <float>,
        "rationale": "<detailed reason for addition citing metrics>",
        "sector": "<sector>"
      }}
    }}
  ]
}}"""


def _strategy_prefilter(universe, strategy_type):
    """Apply strategy-specific pre-filtering on the NSE universe."""
    cfg = PORTFOLIO_STRATEGIES[strategy_type]
    min_price = cfg["min_price"]
    min_tv = cfg["min_traded_value"]
    scoring = cfg["scoring"]

    liquid = [s for s in universe if s["traded_value"] > min_tv and s["close"] > min_price]

    for s in liquid:
        score = 0.0
        cp = s["change_pct"]
        rp = s["range_pct"]
        tv = s["traded_value"]
        close = s["close"]
        high = s.get("high", close)
        low = s.get("low", close)

        # Base: liquidity score
        if tv > 1e9:
            score += 8
        elif tv > 5e8:
            score += 5
        elif tv > 1e8:
            score += 3

        if scoring == "momentum":
            # Forward looking: moderate positive momentum, not extreme
            if 0 < cp < 5:
                score += cp * 3
            elif cp >= 5:
                score += 10
            # Close near high = strength
            if high != low and (close - low) / (high - low) > 0.6:
                score += 4

        elif scoring == "breakout":
            # Quick entry: explosive momentum + volume
            if cp > 2:
                score += min(cp * 2.5, 15)
            if rp > 3:
                score += min(rp * 2, 12)
            if high != low and (close - low) / (high - low) > 0.8:
                score += 6

        elif scoring == "blue_chip":
            # Long term: large cap stability
            if tv > 5e9:
                score += 15
            elif tv > 1e9:
                score += 10
            if abs(cp) < 3:
                score += 5  # Stable
            if close > 500:
                score += 3

        elif scoring == "oversold":
            # Swing: oversold bounces
            if cp < -2:
                score += min(abs(cp) * 2, 12)
            if high != low and (close - low) / (high - low) < 0.3:
                score += 8  # Close near low = potential bounce
            if rp > 2:
                score += 3

        elif scoring == "contrarian":
            # Alpha: contrarian picks — any direction but with volume
            if cp < -1:
                score += min(abs(cp) * 1.5, 8)
            if cp > 1:
                score += min(cp * 1.5, 8)
            if tv > 2e8:
                score += 5

        elif scoring == "value":
            # Value: favor stability and large traded value
            if tv > 5e8:
                score += 8
            if abs(cp) < 2:
                score += 5
            if close > 100:
                score += 3

        s["strategy_score"] = round(score, 2)

    liquid.sort(key=lambda x: x.get("strategy_score", 0), reverse=True)
    return liquid[:80]


def _build_lightweight_shortlist(candidates):
    """Build a lightweight shortlist when yfinance is rate-limited.
    Uses basic bhav copy data + quick yfinance info for top candidates."""
    import yfinance as yf

    shortlist = []
    for c in candidates:
        sym = c["symbol"]
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info or {}

            shortlist.append({
                "symbol": sym,
                "name": c.get("ticker", sym.replace(".NS", "")),
                "sector": info.get("sector", "N/A"),
                "market_data": {
                    "price": c["close"],
                    "change": round(c["close"] - c["prev_close"], 2),
                    "change_pct": c["change_pct"],
                    "volume": c["volume"],
                    "vol_ratio": 1.0,
                },
                "technical": {},
                "fundamental": {
                    "pe_ratio": info.get("trailingPE"),
                    "market_cap": info.get("marketCap"),
                    "roe": info.get("returnOnEquity"),
                    "dividend_yield": info.get("dividendYield"),
                    "sector": info.get("sector", "N/A"),
                    "industry": info.get("industry", "N/A"),
                },
                "prefilter_score": c.get("strategy_score", 0),
            })

            if len(shortlist) >= 20:
                break
            time.sleep(0.5)
        except Exception as e:
            # Even if info fails, include with basic data
            shortlist.append({
                "symbol": sym,
                "name": c.get("ticker", sym.replace(".NS", "")),
                "sector": "N/A",
                "market_data": {
                    "price": c["close"],
                    "change": round(c["close"] - c["prev_close"], 2),
                    "change_pct": c["change_pct"],
                    "volume": c["volume"],
                    "vol_ratio": 1.0,
                },
                "technical": {},
                "fundamental": {},
                "prefilter_score": c.get("strategy_score", 0),
            })
            if len(shortlist) >= 20:
                break

    return shortlist


def _build_lightweight_context(shortlist):
    """Build a text context from lightweight shortlist data."""
    lines = []
    for i, s in enumerate(shortlist):
        md = s.get("market_data", {})
        fd = s.get("fundamental", {})
        lines.append(
            f"[{i+1}] {s['symbol']} ({s.get('name','')}) | {s.get('sector','N/A')}\n"
            f"  Price: ₹{md.get('price', 0):.2f} | Change: {md.get('change_pct', 0):.2f}% | Volume: {md.get('volume', 0):,.0f}\n"
            f"  P/E: {fd.get('pe_ratio', 'N/A')} | Market Cap: {fd.get('market_cap', 'N/A')} | ROE: {fd.get('roe', 'N/A')}\n"
            f"  Dividend Yield: {fd.get('dividend_yield', 'N/A')} | Industry: {fd.get('industry', 'N/A')}\n"
        )
    return "\n".join(lines)


async def construct_portfolio(db, strategy_type: str):
    """
    Construct a portfolio using the God Mode pipeline:
    Universe → Strategy Pre-filter → Deep Features → 3-LLM Consensus → Allocate Capital
    """
    from services.full_market_scanner import get_nse_universe, build_shortlist
    from services.intelligence_engine import _call_llm_in_thread

    import asyncio

    cfg = PORTFOLIO_STRATEGIES.get(strategy_type)
    if not cfg:
        return {"error": f"Unknown strategy: {strategy_type}"}

    logger.info(f"PORTFOLIO: Constructing '{cfg['name']}' portfolio...")

    # Stage 1: Get universe
    universe = get_nse_universe()
    if not universe:
        return {"error": "Failed to load NSE universe"}

    # Stage 2: Strategy pre-filter
    candidates = _strategy_prefilter(universe, strategy_type)
    logger.info(f"PORTFOLIO [{strategy_type}]: {len(candidates)} candidates after pre-filter")

    if len(candidates) < 15:
        return {"error": f"Not enough candidates ({len(candidates)}) for {strategy_type}"}

    # Stage 3: Deep features (technicals + fundamentals) with fallback
    shortlist = build_shortlist(candidates, max_shortlist=15)
    logger.info(f"PORTFOLIO [{strategy_type}]: {len(shortlist)} stocks with deep features")

    use_lightweight = False
    if len(shortlist) < 10:
        # Fallback: build lightweight context from pre-filter data + basic yfinance
        logger.info(f"PORTFOLIO [{strategy_type}]: Shortlist too small, using lightweight mode")
        use_lightweight = True
        shortlist = _build_lightweight_shortlist(candidates[:30])
        logger.info(f"PORTFOLIO [{strategy_type}]: Lightweight shortlist: {len(shortlist)} stocks")

    if len(shortlist) < 10:
        return {"error": f"Not enough data ({len(shortlist)} stocks) for {strategy_type}"}

    # Stage 4: Build context for God Mode
    from services.intelligence_engine import build_batch_context
    if use_lightweight:
        batch_context = _build_lightweight_context(shortlist)
    else:
        batch_context = build_batch_context(shortlist)

    prompt = PORTFOLIO_CONSTRUCTION_PROMPT.format(
        strategy_name=cfg["name"],
        strategy_description=cfg["description"],
        horizon=cfg["horizon"],
    )

    user_text = (
        f"Construct a {cfg['name']} portfolio from these {len(shortlist)} candidates.\n"
        f"Capital: ₹50,00,000. Select EXACTLY 10 stocks.\n\n"
        f"{batch_context}\n\n"
        f"Return ONLY valid JSON."
    )

    # Stage 5: God Mode 3-LLM consensus
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM key not configured"}

    models = [
        ("openai", "gpt-4.1"),
        ("anthropic", "claude-sonnet-4-5-20250929"),
        ("gemini", "gemini-2.5-flash"),
    ]

    logger.info(f"PORTFOLIO [{strategy_type}]: Sending to 3 LLMs in parallel...")
    tasks = [
        asyncio.to_thread(
            _call_llm_in_thread, api_key, prov, model, prompt, user_text, f"pf-{strategy_type}"
        )
        for prov, model in models
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Parse results
    all_selections = []
    model_names = ["openai", "claude", "gemini"]
    model_results = {}
    for name, result in zip(model_names, results):
        if isinstance(result, Exception):
            model_results[name] = {"error": str(result)}
            continue
        if isinstance(result, dict) and "selections" in result:
            model_results[name] = result
            all_selections.append(result)
        elif isinstance(result, dict) and "error" in result:
            model_results[name] = result

    if not all_selections:
        return {"error": "All LLMs failed for portfolio construction", "details": model_results}

    # Synthesize: pick the best selection (most complete with 10 stocks)
    best = max(all_selections, key=lambda x: len(x.get("selections", [])))
    selections = best.get("selections", [])[:10]

    if len(selections) < 5:
        return {"error": f"LLM returned only {len(selections)} stocks, need at least 5"}

    # Normalize weights
    total_weight = sum(s.get("weight", 10) for s in selections)
    for s in selections:
        s["weight"] = round(s.get("weight", 10) / total_weight * 100, 1)

    # Stage 6: Allocate capital and calculate quantities
    holdings = []
    for s in selections:
        entry_price = s.get("entry_price", 0)
        if not entry_price or entry_price <= 0:
            # Try to find from shortlist
            for sl in shortlist:
                sym_check = s.get("symbol", "")
                if sl["symbol"] == sym_check or sl["name"] == sym_check.replace(".NS", ""):
                    entry_price = sl["market_data"]["price"]
                    break
            # Also try matching ticker names
            if not entry_price:
                for sl in shortlist:
                    if sym_check.replace(".NS", "") in sl["symbol"]:
                        entry_price = sl["market_data"]["price"]
                        break
            if not entry_price:
                continue

        allocation = INITIAL_CAPITAL * s["weight"] / 100
        quantity = int(allocation / entry_price)
        if quantity < 1:
            quantity = 1

        holdings.append({
            "symbol": s.get("symbol", ""),
            "name": s.get("name", ""),
            "sector": s.get("sector", ""),
            "entry_price": round(entry_price, 2),
            "current_price": round(entry_price, 2),
            "quantity": quantity,
            "weight": s["weight"],
            "allocation": round(quantity * entry_price, 2),
            "pnl": 0,
            "pnl_pct": 0,
            "conviction": s.get("conviction", "MEDIUM"),
            "rationale": s.get("rationale", ""),
            "key_catalyst": s.get("key_catalyst", ""),
            "entry_date": datetime.now(IST).isoformat(),
        })

    actual_invested = sum(h["allocation"] for h in holdings)

    # Save portfolio
    portfolio_doc = {
        "type": strategy_type,
        "name": cfg["name"],
        "description": cfg["description"],
        "horizon": cfg["horizon"],
        "initial_capital": INITIAL_CAPITAL,
        "actual_invested": round(actual_invested, 2),
        "current_value": round(actual_invested, 2),
        "total_pnl": 0,
        "total_pnl_pct": 0,
        "holdings": holdings,
        "status": "active",
        "created_at": datetime.now(IST).isoformat(),
        "last_analyzed": datetime.now(IST).isoformat(),
        "last_rebalanced": None,
        "portfolio_thesis": best.get("portfolio_thesis", ""),
        "risk_assessment": best.get("risk_assessment", ""),
        "construction_log": {
            "universe_size": len(universe),
            "candidates": len(candidates),
            "shortlist": len(shortlist),
            "models_used": [n for n, r in model_results.items() if "error" not in r],
            "constructed_at": datetime.now(IST).isoformat(),
        },
    }

    await db.portfolios.update_one(
        {"type": strategy_type},
        {"$set": portfolio_doc},
        upsert=True,
    )

    logger.info(f"PORTFOLIO [{strategy_type}]: Constructed with {len(holdings)} stocks, ₹{actual_invested:,.0f} invested")
    return {"status": "constructed", "type": strategy_type, "holdings": len(holdings), "invested": actual_invested}


async def update_portfolio_prices(db, strategy_type: str):
    """Fetch current BSE/yfinance prices and update portfolio P&L."""
    import yfinance as yf

    portfolio = await db.portfolios.find_one({"type": strategy_type}, {"_id": 0})
    if not portfolio or portfolio.get("status") != "active":
        return None

    holdings = portfolio.get("holdings", [])
    total_value = 0

    for h in holdings:
        sym = h.get("symbol", "")
        try:
            ticker = yf.Ticker(sym)
            info = ticker.fast_info
            ltp = getattr(info, "last_price", None) or h["entry_price"]
            h["current_price"] = round(float(ltp), 2)
        except Exception:
            pass  # Keep last known price

        h["pnl"] = round((h["current_price"] - h["entry_price"]) * h["quantity"], 2)
        h["pnl_pct"] = round((h["current_price"] - h["entry_price"]) / h["entry_price"] * 100, 2) if h["entry_price"] else 0
        h["current_value"] = round(h["current_price"] * h["quantity"], 2)
        total_value += h["current_value"]

    total_pnl = round(total_value - portfolio.get("actual_invested", INITIAL_CAPITAL), 2)
    invested = portfolio.get("actual_invested", INITIAL_CAPITAL)
    total_pnl_pct = round(total_pnl / invested * 100, 2) if invested else 0

    await db.portfolios.update_one(
        {"type": strategy_type},
        {"$set": {
            "holdings": holdings,
            "current_value": round(total_value, 2),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "last_analyzed": datetime.now(IST).isoformat(),
        }}
    )

    return {
        "type": strategy_type,
        "current_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "holdings": holdings,
    }


async def evaluate_rebalancing(db, strategy_type: str):
    """
    Evaluate whether a portfolio needs rebalancing using God Mode.
    Runs after market close. Think 100 times.
    """
    from services.full_market_scanner import get_nse_universe
    from services.intelligence_engine import _call_llm_in_thread, build_batch_context

    import asyncio

    portfolio = await db.portfolios.find_one({"type": strategy_type}, {"_id": 0})
    if not portfolio or portfolio.get("status") != "active":
        return {"action": "SKIP", "reason": "Portfolio not active"}

    cfg = PORTFOLIO_STRATEGIES[strategy_type]
    holdings = portfolio.get("holdings", [])

    # Build current holdings summary
    holdings_text = ""
    winners = 0
    losers = 0
    for h in holdings:
        pnl_label = f"+{h['pnl_pct']:.1f}%" if h.get("pnl_pct", 0) >= 0 else f"{h['pnl_pct']:.1f}%"
        holdings_text += (
            f"  {h['symbol']} ({h.get('sector','')}) | Entry: ₹{h['entry_price']:.2f} | "
            f"Current: ₹{h.get('current_price', h['entry_price']):.2f} | P&L: {pnl_label} | "
            f"Weight: {h.get('weight',10):.1f}% | Qty: {h['quantity']} | "
            f"Rationale: {h.get('rationale','')[:80]}\n"
        )
        if h.get("pnl_pct", 0) > 0:
            winners += 1
        elif h.get("pnl_pct", 0) < 0:
            losers += 1

    # Get market candidates for potential replacements
    universe = get_nse_universe()
    if universe:
        candidates = _strategy_prefilter(universe, strategy_type)[:30]
        # Exclude current holdings
        held_syms = {h["symbol"] for h in holdings}
        candidates = [c for c in candidates if c["symbol"] not in held_syms][:15]
    else:
        candidates = []

    from services.full_market_scanner import build_shortlist
    if candidates:
        replacement_shortlist = build_shortlist(candidates, max_shortlist=10)
        candidates_context = build_batch_context(replacement_shortlist) if replacement_shortlist else "No replacement candidates available."
    else:
        candidates_context = "No replacement candidates available."

    created = portfolio.get("created_at", "")
    try:
        days_since = (datetime.now(IST) - datetime.fromisoformat(created)).days
    except Exception:
        days_since = 0

    total_value = portfolio.get("current_value", INITIAL_CAPITAL)
    total_pnl = portfolio.get("total_pnl", 0)
    total_pnl_pct = portfolio.get("total_pnl_pct", 0)

    prompt = PORTFOLIO_REBALANCE_PROMPT.format(
        strategy_name=cfg["name"],
        strategy_description=cfg["description"],
        horizon=cfg["horizon"],
        days_since=days_since,
        current_holdings=holdings_text,
        current_value=f"{total_value:,.0f}",
        total_pnl=f"₹{total_pnl:+,.0f}",
        total_pnl_pct=f"{total_pnl_pct:+.2f}",
        winners=winners,
        losers=losers,
        market_candidates=candidates_context,
    )

    user_text = (
        f"Evaluate {cfg['name']} portfolio for rebalancing.\n"
        f"Think VERY carefully. Only recommend changes with STRONG conviction.\n\n"
        f"Return ONLY valid JSON."
    )

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"action": "ERROR", "reason": "LLM key not configured"}

    # God Mode: 3-LLM parallel evaluation
    models = [
        ("openai", "gpt-4.1"),
        ("anthropic", "claude-sonnet-4-5-20250929"),
        ("gemini", "gemini-2.5-flash"),
    ]

    logger.info(f"REBALANCE [{strategy_type}]: Sending to 3 LLMs...")
    tasks = [
        asyncio.to_thread(
            _call_llm_in_thread, api_key, prov, model, prompt, user_text, f"rebal-{strategy_type}"
        )
        for prov, model in models
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Parse results — majority vote on action
    rebalance_votes = 0
    no_change_votes = 0
    all_analyses = []

    model_names = ["openai", "claude", "gemini"]
    for name, result in zip(model_names, results):
        if isinstance(result, Exception):
            continue
        if isinstance(result, dict):
            all_analyses.append(result)
            if result.get("action") == "REBALANCE":
                rebalance_votes += 1
            else:
                no_change_votes += 1

    if not all_analyses:
        return {"action": "ERROR", "reason": "All LLMs failed"}

    # Consensus: need at least 2 of 3 to agree on rebalancing
    if rebalance_votes >= 2:
        # Find the best rebalance recommendation
        best = max(
            [a for a in all_analyses if a.get("action") == "REBALANCE"],
            key=lambda x: x.get("confidence", 0)
        )
        changes = best.get("changes", [])

        if changes:
            await _execute_rebalance(db, strategy_type, portfolio, changes, best, model_names, results)
            return {"action": "REBALANCE", "changes": len(changes), "analysis": best.get("analysis_summary", "")}

    # Log the no-change decision
    best_analysis = max(all_analyses, key=lambda x: x.get("confidence", 0))
    await db.portfolio_rebalance_log.insert_one({
        "portfolio_type": strategy_type,
        "timestamp": datetime.now(IST).isoformat(),
        "action": "NO_CHANGE",
        "analysis_summary": best_analysis.get("analysis_summary", "Portfolio healthy, no changes needed."),
        "confidence": best_analysis.get("confidence", 0),
        "vote_summary": {"rebalance": rebalance_votes, "no_change": no_change_votes},
        "changes": [],
    })

    return {"action": "NO_CHANGE", "analysis": best_analysis.get("analysis_summary", "")}


async def _execute_rebalance(db, strategy_type, portfolio, changes, analysis, model_names, raw_results):
    """Execute the rebalancing — swap stocks and log rationale."""
    import yfinance as yf

    holdings = portfolio.get("holdings", [])
    holdings_map = {h["symbol"]: h for h in holdings}
    executed_changes = []

    for change in changes[:2]:  # Max 2 changes per cycle
        outgoing_info = change.get("outgoing", {})
        incoming_info = change.get("incoming", {})

        out_sym = outgoing_info.get("symbol", "")
        in_sym = incoming_info.get("symbol", "")

        if not out_sym or not in_sym:
            continue

        # Find outgoing holding
        out_holding = holdings_map.get(out_sym)
        if not out_holding:
            continue

        # Get incoming stock price
        in_price = incoming_info.get("entry_price", 0)
        if not in_price:
            try:
                ticker = yf.Ticker(in_sym)
                in_price = float(getattr(ticker.fast_info, "last_price", 0))
            except Exception:
                continue

        if in_price <= 0:
            continue

        # Calculate swap
        freed_capital = out_holding["current_price"] * out_holding["quantity"]
        new_qty = int(freed_capital / in_price)
        if new_qty < 1:
            new_qty = 1

        out_pnl = round((out_holding.get("current_price", out_holding["entry_price"]) - out_holding["entry_price"]) * out_holding["quantity"], 2)
        out_pnl_pct = round((out_holding.get("current_price", out_holding["entry_price"]) - out_holding["entry_price"]) / out_holding["entry_price"] * 100, 2)

        executed_changes.append({
            "incoming": {
                "symbol": in_sym,
                "name": incoming_info.get("name", ""),
                "entry_price": round(in_price, 2),
                "quantity": new_qty,
                "weight": incoming_info.get("weight", out_holding.get("weight", 10)),
                "rationale": incoming_info.get("rationale", ""),
                "sector": incoming_info.get("sector", ""),
            },
            "outgoing": {
                "symbol": out_sym,
                "name": out_holding.get("name", ""),
                "exit_price": round(out_holding.get("current_price", out_holding["entry_price"]), 2),
                "entry_price": out_holding["entry_price"],
                "quantity": out_holding["quantity"],
                "pnl": out_pnl,
                "pnl_pct": out_pnl_pct,
                "rationale": outgoing_info.get("rationale", ""),
                "held_since": out_holding.get("entry_date", ""),
            },
        })

        # Update holdings: remove outgoing, add incoming
        holdings = [h for h in holdings if h["symbol"] != out_sym]
        holdings.append({
            "symbol": in_sym,
            "name": incoming_info.get("name", ""),
            "sector": incoming_info.get("sector", ""),
            "entry_price": round(in_price, 2),
            "current_price": round(in_price, 2),
            "quantity": new_qty,
            "weight": incoming_info.get("weight", out_holding.get("weight", 10)),
            "allocation": round(new_qty * in_price, 2),
            "pnl": 0,
            "pnl_pct": 0,
            "conviction": "HIGH",
            "rationale": incoming_info.get("rationale", ""),
            "key_catalyst": "",
            "entry_date": datetime.now(IST).isoformat(),
        })

    if executed_changes:
        # Update portfolio holdings
        await db.portfolios.update_one(
            {"type": strategy_type},
            {"$set": {
                "holdings": holdings,
                "last_rebalanced": datetime.now(IST).isoformat(),
            }}
        )

        # Log the rebalance
        await db.portfolio_rebalance_log.insert_one({
            "portfolio_type": strategy_type,
            "timestamp": datetime.now(IST).isoformat(),
            "action": "REBALANCE",
            "analysis_summary": analysis.get("analysis_summary", ""),
            "confidence": analysis.get("confidence", 0),
            "changes": executed_changes,
            "portfolio_value_before": portfolio.get("current_value", 0),
        })

        logger.info(f"REBALANCE [{strategy_type}]: Executed {len(executed_changes)} swaps")


async def get_all_portfolios(db):
    """Get all 6 portfolios with current state."""
    portfolios = await db.portfolios.find({}, {"_id": 0}).to_list(length=10)
    return portfolios


async def get_portfolio(db, strategy_type: str):
    """Get a specific portfolio."""
    return await db.portfolios.find_one({"type": strategy_type}, {"_id": 0})


async def get_rebalance_log(db, strategy_type: str = None, limit: int = 20):
    """Get rebalancing history."""
    query = {}
    if strategy_type:
        query["portfolio_type"] = strategy_type
    logs = await db.portfolio_rebalance_log.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return logs


async def get_portfolio_overview(db):
    """Get high-level overview of all portfolios."""
    portfolios = await get_all_portfolios(db)

    total_invested = 0
    total_value = 0
    total_pnl = 0
    active = 0

    portfolio_summaries = []
    for p in portfolios:
        inv = p.get("actual_invested", INITIAL_CAPITAL)
        val = p.get("current_value", inv)
        pnl = p.get("total_pnl", 0)
        total_invested += inv
        total_value += val
        total_pnl += pnl
        if p.get("status") == "active":
            active += 1

        winners = sum(1 for h in p.get("holdings", []) if h.get("pnl_pct", 0) > 0)
        losers = sum(1 for h in p.get("holdings", []) if h.get("pnl_pct", 0) < 0)

        portfolio_summaries.append({
            "type": p.get("type"),
            "name": p.get("name"),
            "status": p.get("status"),
            "invested": inv,
            "current_value": round(val, 2),
            "total_pnl": round(pnl, 2),
            "total_pnl_pct": p.get("total_pnl_pct", 0),
            "holdings_count": len(p.get("holdings", [])),
            "winners": winners,
            "losers": losers,
            "created_at": p.get("created_at"),
            "last_analyzed": p.get("last_analyzed"),
            "last_rebalanced": p.get("last_rebalanced"),
        })

    # Count pending constructions
    existing_types = {p.get("type") for p in portfolios}
    pending = [t for t in PORTFOLIO_STRATEGIES if t not in existing_types]

    return {
        "total_capital": 6 * INITIAL_CAPITAL,
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_invested * 100, 2) if total_invested else 0,
        "active_portfolios": active,
        "pending_construction": len(pending),
        "pending_types": pending,
        "portfolios": portfolio_summaries,
    }


# ── Autonomous Daemon ─────────────────────────────────────────────────────────

def start_portfolio_daemon(mongo_url: str, db_name: str):
    """
    Background daemon:
    1. On startup: construct any missing portfolios (one at a time)
    2. After market close (4 PM IST): update prices and evaluate rebalancing
    3. Continuous operation without human intervention
    """
    import asyncio as _aio
    from motor.motor_asyncio import AsyncIOMotorClient

    def _daemon_loop():
        logger.info("PORTFOLIO DAEMON: Started — Autonomous Mode")
        time.sleep(60)  # Wait for other services to initialize

        while True:
            try:
                loop = _aio.new_event_loop()
                _aio.set_event_loop(loop)
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]

                # Phase 1: Construct missing portfolios
                existing = loop.run_until_complete(
                    db.portfolios.find({"status": "active"}).distinct("type")
                )
                # Also clean up stuck constructing states
                loop.run_until_complete(
                    db.portfolios.delete_many({"status": {"$in": ["constructing", "error"]}})
                )
                missing = [t for t in PORTFOLIO_STRATEGIES if t not in existing]

                if missing:
                    strategy = missing[0]
                    logger.info(f"PORTFOLIO DAEMON: Constructing '{strategy}'...")
                    # Mark as constructing
                    loop.run_until_complete(db.portfolios.update_one(
                        {"type": strategy},
                        {"$set": {"type": strategy, "status": "constructing", "name": PORTFOLIO_STRATEGIES[strategy]["name"]}},
                        upsert=True,
                    ))
                    try:
                        result = loop.run_until_complete(construct_portfolio(db, strategy))
                        status = result.get('status', result.get('error', 'unknown'))
                        logger.info(f"PORTFOLIO DAEMON: '{strategy}' result: {status}")
                        if 'error' in result:
                            # Revert to pending so it retries next cycle
                            loop.run_until_complete(db.portfolios.delete_one({"type": strategy}))
                    except Exception as e:
                        import traceback
                        logger.error(f"PORTFOLIO DAEMON: Construction failed for {strategy}: {e}\n{traceback.format_exc()}")
                        loop.run_until_complete(db.portfolios.delete_one({"type": strategy}))

                    client.close()
                    loop.close()
                    time.sleep(60)  # Wait between constructions (rate limit buffer)
                    continue

                # Phase 2: Market hours check — update prices periodically
                now = datetime.now(IST)
                hour = now.hour

                if 9 <= hour <= 16:
                    # During/after market hours: update all portfolio prices
                    for strategy_type in PORTFOLIO_STRATEGIES:
                        try:
                            loop.run_until_complete(update_portfolio_prices(db, strategy_type))
                        except Exception as e:
                            logger.debug(f"PORTFOLIO DAEMON: Price update failed for {strategy_type}: {e}")
                        time.sleep(5)

                # Phase 3: After market close (4 PM - 6 PM IST): evaluate rebalancing
                if 16 <= hour <= 18:
                    # Check if already rebalanced today
                    today_str = now.strftime("%Y-%m-%d")
                    for strategy_type in PORTFOLIO_STRATEGIES:
                        last_log = loop.run_until_complete(
                            db.portfolio_rebalance_log.find_one(
                                {"portfolio_type": strategy_type, "timestamp": {"$regex": today_str}},
                                {"_id": 0}
                            )
                        )
                        if last_log:
                            continue  # Already evaluated today

                        logger.info(f"PORTFOLIO DAEMON: Evaluating rebalance for '{strategy_type}'...")
                        try:
                            result = loop.run_until_complete(evaluate_rebalancing(db, strategy_type))
                            logger.info(f"PORTFOLIO DAEMON: Rebalance '{strategy_type}': {result.get('action', 'unknown')}")
                        except Exception as e:
                            logger.error(f"PORTFOLIO DAEMON: Rebalance eval failed for {strategy_type}: {e}")
                        time.sleep(10)

                client.close()
                loop.close()

            except Exception as e:
                logger.error(f"PORTFOLIO DAEMON: Error: {e}")

            # Sleep interval: 5 min during market hours, 30 min otherwise
            now = datetime.now(IST)
            if 9 <= now.hour <= 18:
                time.sleep(300)
            else:
                time.sleep(1800)

    t = threading.Thread(target=_daemon_loop, daemon=True)
    t.start()
    logger.info("PORTFOLIO DAEMON: Thread launched — Autonomous Mode")

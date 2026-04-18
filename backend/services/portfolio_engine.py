"""
Portfolio Engine — Autonomous AI-managed portfolios using God Mode (3-LLM consensus).

HARDENED PIPELINE:
  Stage 1: NSE Universe (bhav copy) → 2400+ stocks
  Stage 2: Liquidity + Price Floor → ~300-500 stocks
  Stage 3: Advanced Fundamental Screener (batch yfinance, screener.in inspired) → ~40-80 stocks
  Stage 4: Deep Enrichment (full technicals + fundamentals + BSE guidance) → ~20-25 stocks
  Stage 5: Hardened LLM Context (structured tables, anti-hallucination, guidance chunks)
  Stage 6: God Mode 3-LLM Consensus with voting overlap

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

from services.portfolio_hardening import (
    validate_fundamentals, validate_technical,
    compute_factor_score, enforce_sector_limits,
    volatility_based_weights, compute_backtest,
)

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
        "screener_criteria": {
            "market_cap_min": 5000e7,
            "revenue_growth_min": 10,
            "roe_min": 10,
            "debt_to_equity_max": 2.0,
        },
    },
    "quick_entry": {
        "name": "Quick Entry",
        "description": "Momentum plays — breakout from consolidation, volume spikes, immediate upside. 1-4 week horizon.",
        "horizon": "1-4 weeks",
        "min_price": 50,
        "min_traded_value": 2e7,
        "scoring": "breakout",
        "screener_criteria": {
            "market_cap_min": 1000e7,
            "volume_spike_min": 1.5,
        },
    },
    "long_term": {
        "name": "Long Term Compounder",
        "description": "Blue-chip compounders — consistent earnings, strong moat, market leaders. 2-5 year horizon.",
        "horizon": "2-5 years",
        "min_price": 200,
        "min_traded_value": 1e8,
        "scoring": "blue_chip",
        "screener_criteria": {
            "market_cap_min": 10000e7,
            "roe_min": 15,
            "debt_to_equity_max": 1.0,
            "profit_margin_min": 8,
        },
    },
    "swing": {
        "name": "Swing Trader",
        "description": "Technical swing trades — stocks at support, RSI oversold, mean reversion setups. 1-2 week horizon.",
        "horizon": "1-2 weeks",
        "min_price": 50,
        "min_traded_value": 2e7,
        "scoring": "oversold",
        "screener_criteria": {
            "market_cap_min": 1000e7,
        },
    },
    "alpha_generator": {
        "name": "Alpha Generator",
        "description": "High-conviction contrarian picks — undervalued, mispriced by market, strong insider buying. Beat the market.",
        "horizon": "3-6 months",
        "min_price": 50,
        "min_traded_value": 5e7,
        "scoring": "contrarian",
        "screener_criteria": {
            "market_cap_min": 2000e7,
            "pe_max": 25,
        },
    },
    "value_stocks": {
        "name": "Value Stocks",
        "description": "Deep value — low P/E, high dividend yield, strong book value, margin of safety. Warren Buffett style.",
        "horizon": "1-3 years",
        "min_price": 50,
        "min_traded_value": 5e7,
        "scoring": "value",
        "screener_criteria": {
            "market_cap_min": 2000e7,
            "pe_max": 20,
            "price_to_book_max": 3.0,
            "debt_to_equity_max": 0.5,
        },
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# HARDENED PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

PORTFOLIO_CONSTRUCTION_PROMPT = """You are the Bharat Market Intel Agent (BMIA) — Tier-1 Quant Analyst, Autonomous Portfolio Construction Engine.

STRATEGY: {strategy_name}
DESCRIPTION: {strategy_description}
INVESTMENT HORIZON: {horizon}
CAPITAL: ₹50,00,000 (50 lakhs)

You will receive an EXHAUSTIVE data packet for each candidate stock containing:
  - Full Technical Analysis (25+ indicators: RSI, MACD, Bollinger, ADX, Stochastic, ATR, OBV, Ichimoku, Moving Averages, Volume Structure Analysis, 52W levels, Fibonacci, Pivot Points)
  - Full Fundamental Analysis (30+ metrics: P/E, P/B, EV/EBITDA, PEG, ROE, ROA, Margins, Growth Rates, D/E, Current Ratio, FCF, Graham Value, Ownership, Quarterly Trends)
  - BSE Corporate Filings Intelligence (Board meetings, insider trading, results, credit ratings, corporate actions from real BSE filings)

═══ ANTI-HALLUCINATION PROTOCOL ═══
1. You MUST ONLY reference data points that appear in the provided context. If a metric says "N/A", do NOT invent a value — acknowledge it is unavailable.
2. When citing a number, use the EXACT value from the data (e.g., "P/E of 18.42" not "P/E around 18").
3. If a stock has missing fundamental data, penalize it in your ranking — incomplete data = higher risk.
4. Do NOT assume positive catalysts unless explicitly mentioned in BSE filings or fundamental trends.
5. Cross-validate: If technicals say BUY but fundamentals are deteriorating, FLAG THE CONFLICT and reduce conviction.

═══ STRATEGY-SPECIFIC EVALUATION RUBRIC ═══
{strategy_rubric}

═══ CONSTRUCTION RULES ═══
1. Select EXACTLY 10 stocks. No more, no less.
2. Weights MUST sum to exactly 100%.
3. Minimum weight per stock: 5%. Maximum: 20%.
4. Diversify across sectors — no more than 3 stocks from the same sector.
5. A BAD STOCK PICK IS AN AI DISCREDIT. Think 100 times before selecting.
6. Entry price must be the current close price from the data.
7. Higher conviction + more data completeness = higher weight allocation.
8. If BSE filings show insider SELLING, it is a RED FLAG — avoid or reduce weight.
9. If quarterly results show DECLINING revenue/profit, it is a RED FLAG — avoid for growth strategies.
10. Prefer stocks where at least 2 of 3 analysis dimensions (technical, fundamental, filings) are favorable.

Return ONLY valid JSON:
{{
  "selections": [
    {{
      "symbol": "<SYMBOL.NS>",
      "name": "<company name>",
      "weight": <float 5-20>,
      "entry_price": <float current close from data>,
      "rationale": "<3-4 sentences citing SPECIFIC metrics: RSI=X, P/E=Y, ROE=Z%, last quarter revenue grew W%>",
      "conviction": "HIGH" | "MEDIUM",
      "sector": "<sector name>",
      "key_catalyst": "<single most important catalyst backed by data>",
      "risk_flag": "<biggest risk for this stock, cite specific data>",
      "technical_signal": "BULLISH" | "NEUTRAL" | "BEARISH",
      "fundamental_grade": "A" | "B" | "C" | "D",
      "filing_insight": "<key finding from BSE filings, or 'No recent filings' if none>"
    }}
  ],
  "portfolio_thesis": "<3-4 sentence thesis grounded in data, not generic statements>",
  "risk_assessment": "<specific risks with data references>",
  "sector_allocation": "<summary of sector diversification>",
  "data_quality_note": "<note on any data gaps that affected selection>"
}}"""

STRATEGY_RUBRICS = {
    "bespoke_forward_looking": """
For BESPOKE FORWARD LOOKING, score stocks on:
  1. GROWTH TRAJECTORY (35%): Revenue growth > 10% YoY, earnings growth positive, quarterly trend improving
  2. FUTURE CATALYSTS (25%): BSE filings showing capacity expansion, new orders, management guidance, credit upgrades
  3. TECHNICAL MOMENTUM (20%): RSI 40-70 (trending but not overbought), MACD bullish, above key MAs
  4. BALANCE SHEET QUALITY (20%): D/E < 2, current ratio > 1, positive FCF, manageable debt
  AVOID: Stocks with declining quarterly revenue, insider selling, high debt, or broken technical structure""",

    "quick_entry": """
For QUICK ENTRY, score stocks on:
  1. MOMENTUM SETUP (40%): RSI 50-70, MACD bullish crossover, price above 20 DMA, volume spike > 1.5x average
  2. BREAKOUT STRUCTURE (30%): Close near 52W high, Bollinger Band expansion, consolidation breakout
  3. VOLUME CONFIRMATION (20%): OBV trending up, above-average volume, institutional activity visible
  4. RISK/REWARD (10%): Clear support level for stop loss, ATR-based target feasible within 1-4 weeks
  AVOID: Stocks in long-term downtrend, with declining volumes, or with upcoming negative catalysts in BSE filings""",

    "long_term": """
For LONG TERM COMPOUNDER, score stocks on:
  1. COMPETITIVE MOAT (30%): ROE > 15%, consistent profit margins, market leadership, strong brand
  2. FINANCIAL FORTRESS (25%): Low D/E < 1, strong current ratio, positive and growing FCF, no debt concerns
  3. GROWTH CONSISTENCY (25%): Revenue + earnings growing consistently over multiple quarters, not one-off spikes
  4. VALUATION SANITY (20%): P/E reasonable for growth rate (PEG < 2), not trading at extreme premiums
  AVOID: Cyclical businesses, high debt companies, businesses with eroding margins, stocks where insiders are net sellers""",

    "swing": """
For SWING TRADER, score stocks on:
  1. OVERSOLD TECHNICAL SETUP (40%): RSI < 35, Stochastic oversold with bullish crossover, price near Bollinger lower band
  2. SUPPORT LEVELS (25%): Price near identified support (Fibonacci, pivot points, 200 DMA), strong buying at lows
  3. MEAN REVERSION SIGNAL (20%): Deviation from 20/50 DMA > 5%, historically mean-reverting stock
  4. VOLUME & LIQUIDITY (15%): Adequate volume for entry/exit, OBV showing accumulation at lows
  AVOID: Stocks in fundamental decline (deteriorating results), those breaking multi-year support, or low liquidity stocks""",

    "alpha_generator": """
For ALPHA GENERATOR, score stocks on:
  1. MISPRICING SIGNAL (35%): P/E below sector average, market cap undervalues earnings power, Graham value > price
  2. CONTRARIAN CATALYST (25%): Insider BUYING (from BSE filings), institutional accumulation, positive corporate actions
  3. HIDDEN VALUE (20%): Strong cash flows not reflected in price, asset-heavy balance sheet, subsidiary value, real estate
  4. TURNAROUND SIGNS (20%): Improving quarterly results after downturn, new management, debt reduction, restructuring
  AVOID: Value traps — stocks cheap for good reason (permanently impaired business, governance issues, secular decline)""",

    "value_stocks": """
For VALUE STOCKS (Buffett-style), score stocks on:
  1. INTRINSIC VALUE DISCOUNT (30%): P/E < 15, P/B < 2, Graham intrinsic value significantly above market price
  2. EARNINGS POWER (25%): Consistent profits (no losses in recent quarters), strong ROE > 12%, stable margins
  3. BALANCE SHEET SAFETY (25%): D/E < 0.5, positive net cash, current ratio > 1.5, no debt red flags
  4. SHAREHOLDER RETURNS (20%): Dividend yield > 2%, sustainable payout ratio, consistent dividend history
  AVOID: High-growth-premium stocks, speculative businesses, companies with negative FCF, aggressive accounting concerns""",
}


PORTFOLIO_REBALANCE_PROMPT = """You are the Bharat Market Intel Agent (BMIA) — Autonomous Portfolio Rebalancing Engine.

STRATEGY: {strategy_name}
DESCRIPTION: {strategy_description}
INVESTMENT HORIZON: {horizon}

═══ CURRENT PORTFOLIO (constructed {days_since} days ago) ═══
{current_holdings}

═══ PORTFOLIO PERFORMANCE ═══
  Initial Capital: ₹50,00,000
  Current Value: ₹{current_value}
  Total P&L: {total_pnl} ({total_pnl_pct}%)
  Winners: {winners} | Losers: {losers}

═══ MARKET CANDIDATES (potential replacements with FULL data) ═══
{market_candidates}

═══ BSE FILING INTELLIGENCE FOR CURRENT HOLDINGS ═══
{holdings_filings}

═══ ANTI-HALLUCINATION PROTOCOL ═══
1. Only reference data from the provided context. Do NOT invent metrics.
2. If filing data shows insider selling for a held stock, this is a STRONG sell signal.
3. If quarterly results show deteriorating revenue/profit, flag it explicitly.
4. Cite exact numbers: "RELIANCE P&L is -3.5%" not "RELIANCE is down."

═══ REBALANCING RULES ═══
1. A BAD STOCK PICK IS AN AI DISCREDIT. Think 100 times before ANY change.
2. DO NOT recommend changes just for the sake of activity. "NO_CHANGE" is perfectly valid.
3. Only recommend replacing a stock if:
   a. Thesis is BROKEN: fundamental deterioration confirmed by quarterly results or BSE filings
   b. Significantly better opportunity: incoming stock must be measurably superior across multiple dimensions
   c. Stop-loss breached: stock has fallen > 8% from entry with no reversal signs
   d. Target achieved: stock has gained > 15% and momentum is fading (RSI > 75, volume declining)
4. Maximum 2 replacements per cycle.
5. For EVERY outgoing stock: cite SPECIFIC data (P&L, broken metric, filing red flag).
6. For EVERY incoming stock: cite SPECIFIC data (why it's better, metrics comparison to outgoing).
7. Preserve sector diversification.

Return ONLY valid JSON:
{{
  "action": "REBALANCE" | "NO_CHANGE",
  "analysis_summary": "<3-4 paragraph analysis of portfolio health, citing specific stock performance and data>",
  "confidence": <int 0-100>,
  "changes": [
    {{
      "outgoing": {{
        "symbol": "<symbol to remove>",
        "rationale": "<detailed reason citing P&L, broken thesis, or specific negative data point>"
      }},
      "incoming": {{
        "symbol": "<SYMBOL.NS>",
        "name": "<company name>",
        "weight": <float>,
        "entry_price": <float>,
        "rationale": "<detailed reason citing superior metrics compared to outgoing>",
        "sector": "<sector>"
      }}
    }}
  ]
}}"""


def _safe_fmt(val, decimals=2, suffix=""):
    if val is None:
        return "N/A"
    try:
        if isinstance(val, bool):
            return "Yes" if val else "No"
        if isinstance(val, (int, float)):
            return f"{round(float(val), decimals)}{suffix}"
        return str(val)
    except Exception:
        return "N/A"


def _fmt_large(val):
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e12:
            return f"₹{val/1e12:.2f}T"
        elif abs(val) >= 1e7:
            return f"₹{val/1e7:.0f}Cr"
        elif abs(val) >= 1e5:
            return f"₹{val/1e5:.1f}L"
        else:
            return f"₹{val:,.0f}"
    except Exception:
        return "N/A"


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: ADVANCED SCREENER (screener.in inspired)
# ═══════════════════════════════════════════════════════════════════════════════

def _basic_liquidity_filter(universe, strategy_type):
    """Stage 2: Basic liquidity + price floor from bhav copy data."""
    cfg = PORTFOLIO_STRATEGIES[strategy_type]
    min_price = cfg["min_price"]
    min_tv = cfg["min_traded_value"]
    return [s for s in universe if s["traded_value"] > min_tv and s["close"] > min_price]


def _batch_fetch_fundamentals(symbols, batch_size=5, delay=1.0):
    """Batch-fetch fundamental snapshots from yfinance with rate limiting.
    Returns dict: symbol → {market_cap, pe, pb, roe, de, div_yield, sector, ...}
    """
    import yfinance as yf

    results = {}
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        for sym in batch:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info or {}
                results[sym] = {
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                    "forward_pe": info.get("forwardPE"),
                    "price_to_book": info.get("priceToBook"),
                    "peg_ratio": info.get("pegRatio"),
                    "ev_to_ebitda": info.get("enterpriseToEbitda"),
                    "roe": info.get("returnOnEquity"),
                    "roa": info.get("returnOnAssets"),
                    "profit_margin": info.get("profitMargins"),
                    "operating_margin": info.get("operatingMargins"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "earnings_growth": info.get("earningsGrowth"),
                    "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio": info.get("currentRatio"),
                    "free_cashflow": info.get("freeCashflow"),
                    "dividend_yield": info.get("dividendYield"),
                    "beta": info.get("beta"),
                    "sector": info.get("sector", "N/A"),
                    "industry": info.get("industry", "N/A"),
                    "held_pct_insiders": info.get("heldPercentInsiders"),
                    "held_pct_institutions": info.get("heldPercentInstitutions"),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                    "eps": info.get("trailingEps"),
                    "book_value": info.get("bookValue"),
                    "shares_outstanding": info.get("sharesOutstanding"),
                }
            except Exception as e:
                logger.debug(f"Fundamentals fetch failed for {sym}: {e}")
                results[sym] = None
        if i + batch_size < len(symbols):
            time.sleep(delay)
    return results


def _advanced_screener(universe, strategy_type):
    """
    Stage 3: Advanced fundamental screener inspired by screener.in.
    Applies strategy-specific fundamental criteria on top of bhav copy data.
    """
    cfg = PORTFOLIO_STRATEGIES[strategy_type]
    scoring = cfg["scoring"]
    screener = cfg.get("screener_criteria", {})

    # Stage 2: Basic liquidity filter
    liquid = _basic_liquidity_filter(universe, strategy_type)
    logger.info(f"SCREENER [{strategy_type}]: {len(liquid)} after liquidity filter")

    # Pre-score by bhav copy data to pick top candidates for fundamental screening
    for s in liquid:
        score = 0.0
        cp = s["change_pct"]
        tv = s["traded_value"]
        close = s["close"]
        high = s.get("high", close)
        low = s.get("low", close)

        # Liquidity score
        if tv > 1e9:
            score += 8
        elif tv > 5e8:
            score += 5
        elif tv > 1e8:
            score += 3

        # Strategy-specific bhav copy scoring
        if scoring == "momentum":
            if 0 < cp < 5:
                score += cp * 3
            elif cp >= 5:
                score += 10
            if high != low and (close - low) / (high - low) > 0.6:
                score += 4
        elif scoring == "breakout":
            if cp > 2:
                score += min(cp * 2.5, 15)
            if high != low and (close - low) / (high - low) > 0.8:
                score += 6
        elif scoring == "blue_chip":
            if tv > 5e9:
                score += 15
            elif tv > 1e9:
                score += 10
            if abs(cp) < 3:
                score += 5
        elif scoring == "oversold":
            if cp < -2:
                score += min(abs(cp) * 2, 12)
            if high != low and (close - low) / (high - low) < 0.3:
                score += 8
        elif scoring == "contrarian":
            if cp < -1:
                score += min(abs(cp) * 1.5, 8)
            if tv > 2e8:
                score += 5
        elif scoring == "value":
            if tv > 5e8:
                score += 8
            if abs(cp) < 2:
                score += 5

        s["bhav_score"] = round(score, 2)

    liquid.sort(key=lambda x: x.get("bhav_score", 0), reverse=True)

    # Take top 80 for fundamental screening (rate limit conscious)
    top_for_screening = liquid[:80]
    symbols_to_screen = [s["symbol"] for s in top_for_screening]

    logger.info(f"SCREENER [{strategy_type}]: Fetching fundamentals for {len(symbols_to_screen)} stocks...")
    fund_data = _batch_fetch_fundamentals(symbols_to_screen, batch_size=5, delay=0.8)

    # Apply fundamental screener criteria
    screened = []
    for s in top_for_screening:
        sym = s["symbol"]
        fd = fund_data.get(sym)
        if fd is None:
            continue

        # Store fundamental snapshot on the candidate
        s["fund_snapshot"] = fd

        # Market cap check
        mc = fd.get("market_cap")
        mc_min = screener.get("market_cap_min")
        if mc_min and (mc is None or mc < mc_min):
            continue

        # Strategy-specific fundamental filters
        passes = True

        if "pe_max" in screener:
            pe = fd.get("pe_ratio")
            if pe is not None and pe > screener["pe_max"]:
                passes = False

        if "price_to_book_max" in screener:
            pb = fd.get("price_to_book")
            if pb is not None and pb > screener["price_to_book_max"]:
                passes = False

        if "roe_min" in screener:
            roe = fd.get("roe")
            if roe is not None and roe < screener["roe_min"] / 100:
                passes = False

        if "debt_to_equity_max" in screener:
            de = fd.get("debt_to_equity")
            if de is not None and de > screener["debt_to_equity_max"] * 100:
                passes = False

        if "revenue_growth_min" in screener:
            rg = fd.get("revenue_growth")
            if rg is not None and rg < screener["revenue_growth_min"] / 100:
                passes = False

        if "profit_margin_min" in screener:
            pm = fd.get("profit_margin")
            if pm is not None and pm < screener["profit_margin_min"] / 100:
                passes = False

        if not passes:
            continue

        # Composite score: bhav + fundamental quality
        fund_score = 0
        pe = fd.get("pe_ratio")
        roe = fd.get("roe")
        rg = fd.get("revenue_growth")
        eg = fd.get("earnings_growth")
        de = fd.get("debt_to_equity")
        pm = fd.get("profit_margin")
        dy = fd.get("dividend_yield")

        if roe and roe > 0.15:
            fund_score += 10
        if rg and rg > 0.10:
            fund_score += 8
        if eg and eg > 0.10:
            fund_score += 8
        if pm and pm > 0.10:
            fund_score += 5
        if de is not None and de < 50:
            fund_score += 5
        if pe and 0 < pe < 30:
            fund_score += 5
        if dy and dy > 0.01:
            fund_score += 3

        s["fund_score"] = fund_score
        s["composite_score"] = round(s["bhav_score"] + fund_score, 2)
        screened.append(s)

    screened.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    logger.info(f"SCREENER [{strategy_type}]: {len(screened)} passed advanced screening")
    return screened[:40]


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 4: DEEP ENRICHMENT (technicals + full fundamentals + guidance)
# ═══════════════════════════════════════════════════════════════════════════════

def _deep_enrich(candidates, max_shortlist=20):
    """Build deeply enriched shortlist with full technicals + fundamentals."""
    import yfinance as yf
    from services.technical_service import full_technical_analysis
    from services.fundamental_service import get_fundamentals

    shortlist = []
    for c in candidates:
        if len(shortlist) >= max_shortlist:
            break
        sym = c["symbol"]
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="3mo")
            if hist is None or len(hist) < 20:
                continue

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

            technical = full_technical_analysis(ohlcv)
            fundamentals = get_fundamentals(sym)

            # HARDENING: Validate data before it reaches any LLM
            fundamentals = validate_fundamentals(fundamentals) if isinstance(fundamentals, dict) else fundamentals
            technical = validate_technical(technical) if isinstance(technical, dict) else technical

            # Volume ratio
            if len(hist) >= 11:
                current_vol = float(hist["Volume"].iloc[-1])
                avg_vol_10d = float(hist["Volume"].iloc[-11:-1].mean())
                vol_ratio = round(current_vol / max(avg_vol_10d, 1), 1)
            else:
                vol_ratio = 1.0

            shortlist.append({
                "symbol": sym,
                "name": c.get("ticker", sym.replace(".NS", "")),
                "sector": fundamentals.get("sector", c.get("fund_snapshot", {}).get("sector", "N/A")) if isinstance(fundamentals, dict) else "N/A",
                "market_data": {
                    "price": c["close"],
                    "change": round(c["close"] - c["prev_close"], 2),
                    "change_pct": c["change_pct"],
                    "volume": c["volume"],
                    "vol_ratio": vol_ratio,
                },
                "technical": technical if isinstance(technical, dict) else {},
                "fundamental": fundamentals if isinstance(fundamentals, dict) else {},
                "bhav_score": c.get("bhav_score", 0),
                "fund_score": c.get("fund_score", 0),
                "composite_score": c.get("composite_score", 0),
            })
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"Deep enrich skip {sym}: {e}")
    logger.info(f"DEEP ENRICH: {len(shortlist)} stocks with full data")
    return shortlist


def _build_lightweight_shortlist(candidates):
    """Fallback when deep enrich fails — basic yfinance info."""
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
                "bhav_score": c.get("bhav_score", 0),
                "fund_score": c.get("fund_score", 0),
                "composite_score": c.get("composite_score", 0),
            })
            if len(shortlist) >= 20:
                break
            time.sleep(0.5)
        except Exception:
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
                "bhav_score": c.get("bhav_score", 0),
                "fund_score": c.get("fund_score", 0),
                "composite_score": c.get("composite_score", 0),
            })
            if len(shortlist) >= 20:
                break
    return shortlist


# ═══════════════════════════════════════════════════════════════════════════════
# GUIDANCE INTEGRATION — Pull BSE filings for shortlisted stocks
# ═══════════════════════════════════════════════════════════════════════════════

async def _fetch_guidance_for_stocks(db, stock_tickers):
    """Fetch recent BSE filings for a list of stock tickers."""
    ticker_to_filings = {}
    for ticker in stock_tickers:
        clean = ticker.replace(".NS", "").replace(".BO", "")
        # Search guidance collection for matching stock_symbol
        cursor = db.guidance.find(
            {"stock_symbol": {"$regex": clean, "$options": "i"}},
            {"_id": 0, "headline": 1, "category": 1, "news_date": 1,
             "stock_symbol": 1, "stock_name": 1, "more_text": 1,
             "pdf_text_chunks": 1, "critical": 1}
        ).sort("news_date", -1).limit(5)
        filings = await cursor.to_list(length=5)
        if filings:
            ticker_to_filings[ticker] = filings
    return ticker_to_filings


def _build_filing_context(filings_list):
    """Build text context from BSE filings for a single stock."""
    if not filings_list:
        return "No recent BSE filings found."
    lines = []
    for f in filings_list[:5]:
        date_str = f.get("news_date", "")
        if isinstance(date_str, str) and len(date_str) > 10:
            date_str = date_str[:10]
        cat = f.get("category", "")
        headline = f.get("headline", "")
        critical = " [CRITICAL]" if f.get("critical") else ""
        lines.append(f"  [{date_str}] {cat}{critical}: {headline}")
        more = f.get("more_text", "")
        if more:
            lines.append(f"    Detail: {more[:200]}")
        # Include first chunk of PDF text if available
        chunks = f.get("pdf_text_chunks", [])
        if chunks:
            first_chunk = str(chunks[0])[:300].replace("\n", " ").strip()
            lines.append(f"    Filing excerpt: {first_chunk}")
    return "\n".join(lines) if lines else "No recent BSE filings found."


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 5: HARDENED CONTEXT BUILDING
# ═══════════════════════════════════════════════════════════════════════════════

def _build_hardened_context(shortlist, guidance_data):
    """Build an exhaustive, structured context for each candidate stock."""
    parts = []
    parts.append(f"{'═'*70}")
    parts.append(f"  CANDIDATE STOCKS: {len(shortlist)} stocks with FULL analysis data")
    parts.append(f"  Generated: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    parts.append(f"{'═'*70}\n")

    for i, stock in enumerate(shortlist):
        sym = stock.get("symbol", "?")
        clean = sym.replace(".NS", "")
        parts.append(f"\n{'━'*70}")
        parts.append(f"  STOCK [{i+1}/{len(shortlist)}]: {clean} ({sym})")
        parts.append(f"  Sector: {stock.get('sector', 'N/A')} | Screener Score: {stock.get('composite_score', 'N/A')}")
        parts.append(f"{'━'*70}")

        # ── PRICE DATA ──
        md = stock.get("market_data", {})
        parts.append("\n  ▌ PRICE DATA")
        parts.append(f"    Price: ₹{_safe_fmt(md.get('price'))} | Change: {_safe_fmt(md.get('change_pct'), suffix='%')}")
        parts.append(f"    Volume: {md.get('volume', 0):,} | Vol Ratio (vs 10d avg): {_safe_fmt(md.get('vol_ratio'))}x")

        # ── FULL TECHNICAL ANALYSIS ──
        tech = stock.get("technical", {})
        if tech and not tech.get("error"):
            parts.append("\n  ▌ TECHNICAL ANALYSIS (25+ indicators)")
            rsi = tech.get("rsi", {})
            macd = tech.get("macd", {})
            bb = tech.get("bollinger", {})
            adx = tech.get("adx", {})
            stoch = tech.get("stochastic", {})
            atr = tech.get("atr", {})
            obv = tech.get("obv", {})
            ma = tech.get("moving_averages", {})
            ich = tech.get("ichimoku", {})
            pa = tech.get("price_action", {})
            bk = tech.get("breakout", {})
            fib = tech.get("fibonacci", {})
            pivot = tech.get("pivot_points", {})
            wr = tech.get("williams_r", {})
            cci = tech.get("cci", {})
            roc = tech.get("roc", {})
            vsa = tech.get("vsa", {})

            parts.append(f"    RSI(14): {_safe_fmt(rsi.get('current'))} | Zone: {'Overbought' if (rsi.get('current') or 50)>70 else 'Oversold' if (rsi.get('current') or 50)<30 else 'Neutral'}")
            parts.append(f"    MACD: Line={_safe_fmt(macd.get('line'),4)} Signal={_safe_fmt(macd.get('signal'),4)} Hist={_safe_fmt(macd.get('histogram'),4)} Cross={macd.get('crossover','N/A')}")
            parts.append(f"    Bollinger: %B={_safe_fmt(bb.get('percent_b'),3)} BW={_safe_fmt(bb.get('bandwidth'),suffix='%')} Squeeze={_safe_fmt(bb.get('squeeze'))} Pos={bb.get('position','N/A')}")
            parts.append(f"    ADX(14): {_safe_fmt(adx.get('adx'))} +DI={_safe_fmt(adx.get('plus_di'))} -DI={_safe_fmt(adx.get('minus_di'))} Str={adx.get('trend_strength','N/A')} Dir={adx.get('direction','N/A')}")
            parts.append(f"    Stochastic: %K={_safe_fmt(stoch.get('k'))} %D={_safe_fmt(stoch.get('d'))} Zone={stoch.get('zone','N/A')} Cross={stoch.get('crossover','N/A')}")
            parts.append(f"    ATR(14): {_safe_fmt(atr.get('atr'))} ATR%={_safe_fmt(atr.get('atr_pct'),suffix='%')} Vol={atr.get('volatility','N/A')}")
            parts.append(f"    OBV: Trend={obv.get('trend','N/A')} | VSA: {vsa.get('signal','N/A')}")
            parts.append(f"    Williams%R: {_safe_fmt(wr.get('value'))} Zone={wr.get('zone','N/A')}")
            parts.append(f"    CCI: {_safe_fmt(cci.get('value'))} Zone={cci.get('zone','N/A')}")
            parts.append(f"    ROC: {_safe_fmt(roc.get('value'))}")
            parts.append(f"    MAs: AboveAll={_safe_fmt(ma.get('above_all_ma'))} GoldenCross={_safe_fmt(ma.get('golden_cross'))} DeathCross={_safe_fmt(ma.get('death_cross'))}")
            parts.append(f"    Ichimoku: Cloud={ich.get('cloud_signal','N/A')} TK={ich.get('tk_cross','N/A')} PriceVsCloud={ich.get('price_vs_cloud','N/A')}")
            parts.append(f"    52W: HighDist={_safe_fmt(bk.get('distance_from_high_pct'),suffix='%')} LowDist={_safe_fmt(bk.get('distance_from_low_pct'),suffix='%')} Consolidation={_safe_fmt(bk.get('consolidation_30d'))}")
            parts.append(f"    Trend: 20d={pa.get('trend_20d','N/A')} 50d={pa.get('trend_50d','N/A')}")

            if fib:
                parts.append(f"    Fibonacci: S1={_safe_fmt(fib.get('s1'))} S2={_safe_fmt(fib.get('s2'))} R1={_safe_fmt(fib.get('r1'))} R2={_safe_fmt(fib.get('r2'))}")
            if pivot:
                parts.append(f"    Pivots: PP={_safe_fmt(pivot.get('pp'))} S1={_safe_fmt(pivot.get('s1'))} R1={_safe_fmt(pivot.get('r1'))}")

            ts = tech.get("technical_score")
            if ts is not None:
                parts.append(f"    Technical Score: {_safe_fmt(ts)}/100")
        else:
            parts.append("\n  ▌ TECHNICAL ANALYSIS: Not available (data insufficient)")

        # ── FULL FUNDAMENTAL ANALYSIS ──
        fund = stock.get("fundamental", {})
        if fund and not fund.get("error"):
            parts.append("\n  ▌ FUNDAMENTAL ANALYSIS (30+ metrics)")
            parts.append("    Valuation:")
            parts.append(f"      P/E: {_safe_fmt(fund.get('pe_ratio'))} | Fwd P/E: {_safe_fmt(fund.get('forward_pe'))} | PEG: {_safe_fmt(fund.get('peg_ratio'))}")
            parts.append(f"      P/B: {_safe_fmt(fund.get('price_to_book'))} | P/S: {_safe_fmt(fund.get('price_to_sales'))} | EV/EBITDA: {_safe_fmt(fund.get('ev_to_ebitda'))}")
            parts.append(f"      Graham Value: ₹{_safe_fmt(fund.get('graham_value'))} | Valuation: {fund.get('valuation','N/A')}")
            parts.append(f"      Market Cap: {_fmt_large(fund.get('market_cap'))}")

            parts.append("    Profitability:")
            parts.append(f"      ROE: {_safe_fmt(fund.get('roe'),suffix='%')} | ROA: {_safe_fmt(fund.get('roa'),suffix='%')}")
            parts.append(f"      Profit Margin: {_safe_fmt(fund.get('profit_margin'),suffix='%')} | OPM: {_safe_fmt(fund.get('operating_margin'),suffix='%')} | Gross: {_safe_fmt(fund.get('gross_margin'),suffix='%')}")

            parts.append("    Growth:")
            parts.append(f"      Revenue Growth: {_safe_fmt(fund.get('revenue_growth'),suffix='%')} | Earnings Growth: {_safe_fmt(fund.get('earnings_growth'),suffix='%')}")
            parts.append(f"      Quarterly Earnings Growth: {_safe_fmt(fund.get('earnings_quarterly_growth'),suffix='%')}")

            parts.append("    Balance Sheet:")
            parts.append(f"      D/E: {_safe_fmt(fund.get('debt_to_equity'))} | Current Ratio: {_safe_fmt(fund.get('current_ratio'))} | Quick Ratio: {_safe_fmt(fund.get('quick_ratio'))}")
            parts.append(f"      Total Debt: {_fmt_large(fund.get('total_debt'))} | Net Cash: {_fmt_large(fund.get('net_cash'))} | D/EBITDA: {_safe_fmt(fund.get('debt_to_ebitda'))}")

            parts.append("    Cash Flow:")
            parts.append(f"      FCF: {_fmt_large(fund.get('free_cashflow'))} | OpCF: {_fmt_large(fund.get('operating_cashflow'))} | FCF Yield: {_safe_fmt(fund.get('fcf_yield'),suffix='%')}")

            parts.append("    Shareholder:")
            parts.append(f"      EPS: {_safe_fmt(fund.get('eps'))} | BVPS: {_safe_fmt(fund.get('bvps'))} | Div Yield: {_safe_fmt(fund.get('dividend_yield'),suffix='%')} | Payout: {_safe_fmt(fund.get('payout_ratio'),suffix='%')}")

            parts.append("    Ownership:")
            parts.append(f"      Insider%: {_safe_fmt(fund.get('held_pct_insiders'),suffix='%')} | Institutions%: {_safe_fmt(fund.get('held_pct_institutions'),suffix='%')} | Beta: {_safe_fmt(fund.get('beta'))}")
            parts.append(f"      52W High: ₹{_safe_fmt(fund.get('fifty_two_week_high'))} | 52W Low: ₹{_safe_fmt(fund.get('fifty_two_week_low'))}")

            # Quarterly trends
            qr = fund.get("quarterly_revenue", [])
            qe = fund.get("quarterly_earnings", [])
            if qr:
                parts.append("    Quarterly Revenue Trend:")
                for q in qr[:4]:
                    parts.append(f"      {q.get('quarter','?')}: {_fmt_large(q.get('revenue'))}")
            if qe:
                parts.append("    Quarterly Net Income Trend:")
                for q in qe[:4]:
                    parts.append(f"      {q.get('quarter','?')}: {_fmt_large(q.get('net_income'))}")

            fs = fund.get("fundamental_score")
            if fs is not None:
                parts.append(f"    Fundamental Score: {_safe_fmt(fs)}/100")
        else:
            parts.append("\n  ▌ FUNDAMENTAL ANALYSIS: Limited data available")
            # Show whatever screener data we have
            snap = stock.get("fund_snapshot", {})
            if snap:
                parts.append(f"    P/E: {_safe_fmt(snap.get('pe_ratio'))} | P/B: {_safe_fmt(snap.get('price_to_book'))} | ROE: {_safe_fmt(snap.get('roe'))}")
                parts.append(f"    Market Cap: {_fmt_large(snap.get('market_cap'))} | D/E: {_safe_fmt(snap.get('debt_to_equity'))}")

        # ── BSE FILING INTELLIGENCE ──
        filings = guidance_data.get(sym, [])
        parts.append("\n  ▌ BSE CORPORATE FILINGS")
        parts.append(f"    {_build_filing_context(filings)}")

        parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 6: PORTFOLIO CONSTRUCTION (Hardened)
# ═══════════════════════════════════════════════════════════════════════════════

async def construct_portfolio(db, strategy_type: str):
    """
    HARDENED PIPELINE:
    Universe → Advanced Screener → Deep Enrichment → Guidance Integration → 3-LLM Consensus → Voting → Allocate
    """
    from services.full_market_scanner import get_nse_universe, build_shortlist
    from services.intelligence_engine import _call_llm_in_thread

    import asyncio

    cfg = PORTFOLIO_STRATEGIES.get(strategy_type)
    if not cfg:
        return {"error": f"Unknown strategy: {strategy_type}"}

    # Hard rule: portfolio construction only during safe market hours
    from utils.market_hours import is_market_safe
    ok, reason = await is_market_safe(db)
    if not ok:
        logger.info(f"CONSTRUCT [{strategy_type}]: skipped — {reason}")
        return {"error": reason, "market_closed": True}

    logger.info(f"PORTFOLIO: Constructing '{cfg['name']}' with HARDENED pipeline...")

    # Stage 1: Get universe
    universe = get_nse_universe()
    if not universe:
        return {"error": "Failed to load NSE universe"}

    # Stage 3: Advanced screener (replaces old primitive pre-filter)
    candidates = _advanced_screener(universe, strategy_type)
    logger.info(f"PORTFOLIO [{strategy_type}]: {len(candidates)} passed advanced screener")

    if len(candidates) < 10:
        return {"error": f"Not enough candidates ({len(candidates)}) passed screening for {strategy_type}"}

    # Stage 4: Deep enrichment (full technicals + fundamentals)
    shortlist = _deep_enrich(candidates, max_shortlist=20)
    logger.info(f"PORTFOLIO [{strategy_type}]: {len(shortlist)} stocks deeply enriched")

    if len(shortlist) < 10:
        logger.info(f"PORTFOLIO [{strategy_type}]: Deep enrich insufficient, using lightweight fallback")
        shortlist = _build_lightweight_shortlist(candidates[:30])
        logger.info(f"PORTFOLIO [{strategy_type}]: Lightweight shortlist: {len(shortlist)} stocks")

    if len(shortlist) < 10:
        return {"error": f"Not enough data ({len(shortlist)} stocks) for {strategy_type}"}

    # Stage 4b: Fetch BSE guidance data for shortlisted stocks
    stock_tickers = [s["symbol"] for s in shortlist]
    guidance_data = await _fetch_guidance_for_stocks(db, stock_tickers)
    logger.info(f"PORTFOLIO [{strategy_type}]: Guidance data found for {len(guidance_data)} stocks")

    # Stage 5: Build hardened context
    batch_context = _build_hardened_context(shortlist, guidance_data)

    strategy_rubric = STRATEGY_RUBRICS.get(strategy_type, "")
    prompt = PORTFOLIO_CONSTRUCTION_PROMPT.format(
        strategy_name=cfg["name"],
        strategy_description=cfg["description"],
        horizon=cfg["horizon"],
        strategy_rubric=strategy_rubric,
    )

    user_text = (
        f"Construct a {cfg['name']} portfolio from these {len(shortlist)} candidates.\n"
        f"Capital: ₹50,00,000. Select EXACTLY 10 stocks.\n"
        f"All data below is REAL and verified. Only reference what you see.\n\n"
        f"{batch_context}\n\n"
        f"Return ONLY valid JSON."
    )

    # Stage 6: God Mode 3-LLM consensus
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

    # Parse results with VOTING
    all_selections = []
    model_names = ["openai", "claude", "gemini"]
    model_results = {}
    for name, result in zip(model_names, results):
        if isinstance(result, Exception):
            model_results[name] = {"error": str(result)}
            logger.error(f"PORTFOLIO [{strategy_type}]: LLM {name} exception: {result}")
            continue
        if isinstance(result, dict) and "selections" in result:
            model_results[name] = result
            all_selections.append((name, result))
            logger.info(f"PORTFOLIO [{strategy_type}]: LLM {name} returned {len(result.get('selections', []))} selections")
        elif isinstance(result, dict) and "error" in result:
            model_results[name] = result
            logger.warning(f"PORTFOLIO [{strategy_type}]: LLM {name} returned error: {result.get('error', '')[:100]}")
        else:
            model_results[name] = {"error": f"Unexpected response type: {type(result)}"}
            logger.warning(f"PORTFOLIO [{strategy_type}]: LLM {name} unexpected: {str(result)[:100]}")

    if not all_selections:
        logger.error(f"PORTFOLIO [{strategy_type}]: All LLMs failed. Details: {json.dumps({k: v.get('error', 'no error key') if isinstance(v, dict) else str(v)[:50] for k, v in model_results.items()})}")
        return {"error": "All LLMs failed for portfolio construction", "details": model_results}

    # CONSENSUS: Count how many LLMs picked each stock
    stock_votes = {}
    for model_name, result in all_selections:
        for sel in result.get("selections", []):
            sym = sel.get("symbol", "")
            if sym not in stock_votes:
                stock_votes[sym] = {"count": 0, "models": [], "selections": []}
            stock_votes[sym]["count"] += 1
            stock_votes[sym]["models"].append(model_name)
            stock_votes[sym]["selections"].append(sel)

    # Prefer stocks picked by 2+ models, then fill with single-vote high-conviction
    consensus_picks = []
    multi_vote = sorted(
        [(sym, v) for sym, v in stock_votes.items() if v["count"] >= 2],
        key=lambda x: x[1]["count"], reverse=True
    )
    for sym, v in multi_vote:
        # Merge: take the selection with most detail
        best_sel = max(v["selections"], key=lambda s: len(s.get("rationale", "")))
        best_sel["consensus_votes"] = v["count"]
        best_sel["consensus_models"] = v["models"]
        consensus_picks.append(best_sel)

    # Fill remaining slots from single-vote picks (by best model's full list)
    if len(consensus_picks) < 10:
        best_model_result = max(all_selections, key=lambda x: len(x[1].get("selections", [])))
        for sel in best_model_result[1].get("selections", []):
            sym = sel.get("symbol", "")
            if sym not in [p.get("symbol") for p in consensus_picks]:
                sel["consensus_votes"] = stock_votes.get(sym, {}).get("count", 1)
                sel["consensus_models"] = stock_votes.get(sym, {}).get("models", [best_model_result[0]])
                consensus_picks.append(sel)
            if len(consensus_picks) >= 10:
                break

    selections = consensus_picks[:10]

    if len(selections) < 5:
        return {"error": f"Consensus yielded only {len(selections)} stocks, need at least 5"}

    # ══════════════════════════════════════════════════════════════════════════
    # HARDENING LAYER 1: Compute factor scores for each selection
    # ══════════════════════════════════════════════════════════════════════════
    shortlist_map = {s["symbol"]: s for s in shortlist}
    for sel in selections:
        sym = sel.get("symbol", "")
        sl_data = shortlist_map.get(sym, {})
        sel["factor_score"] = compute_factor_score(sl_data, strategy_type)
        if not sel.get("sector"):
            sel["sector"] = sl_data.get("sector", "Other")

    # ══════════════════════════════════════════════════════════════════════════
    # HARDENING LAYER 2: Enforce sector diversification (max 3 per sector)
    # ══════════════════════════════════════════════════════════════════════════
    compliant, overflow = enforce_sector_limits(selections, max_per_sector=3)
    if len(compliant) < 10 and overflow:
        # Replace overflow slots with remaining candidates from other sectors
        remaining_syms = {s.get("symbol") for s in compliant}
        for sv_item in sorted(stock_votes.items(), key=lambda x: x[1]["count"], reverse=True):
            sv_sym, sv_data = sv_item
            if sv_sym in remaining_syms:
                continue
            # Check sector
            sl_d = shortlist_map.get(sv_sym, {})
            sec = sl_d.get("sector", "Other") or "Other"
            sec_count = sum(1 for c in compliant if (c.get("sector") or "Other") == sec)
            if sec_count < 3:
                best_sel = max(sv_data["selections"], key=lambda s: len(s.get("rationale", "")))
                best_sel["sector"] = sec
                best_sel["factor_score"] = compute_factor_score(sl_d, strategy_type)
                best_sel["consensus_votes"] = sv_data["count"]
                best_sel["consensus_models"] = sv_data["models"]
                compliant.append(best_sel)
                remaining_syms.add(sv_sym)
            if len(compliant) >= 10:
                break

    selections = compliant[:10]
    logger.info(f"PORTFOLIO [{strategy_type}]: {len(selections)} stocks after sector enforcement")

    if len(selections) < 5:
        return {"error": f"After sector enforcement, only {len(selections)} stocks remain"}

    # ══════════════════════════════════════════════════════════════════════════
    # HARDENING LAYER 3: Volatility-based sizing (code decides weights)
    # ══════════════════════════════════════════════════════════════════════════
    for sel in selections:
        sym = sel.get("symbol", "")
        sl_data = shortlist_map.get(sym, {})
        sel["technical"] = sl_data.get("technical", {})

    selections = volatility_based_weights(selections, min_weight=5.0, max_weight=20.0)
    logger.info(f"PORTFOLIO [{strategy_type}]: Volatility-based weights applied")

    # Allocate capital and calculate quantities
    holdings = []
    for s in selections:
        entry_price = s.get("entry_price", 0)
        if not entry_price or entry_price <= 0:
            for sl in shortlist:
                sym_check = s.get("symbol", "")
                if sl["symbol"] == sym_check or sl["name"] == sym_check.replace(".NS", ""):
                    entry_price = sl["market_data"]["price"]
                    break
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
            "risk_flag": s.get("risk_flag", ""),
            "technical_signal": s.get("technical_signal", ""),
            "fundamental_grade": s.get("fundamental_grade", ""),
            "filing_insight": s.get("filing_insight", ""),
            "factor_score": s.get("factor_score", 0),
            "consensus_votes": s.get("consensus_votes", 1),
            "consensus_models": s.get("consensus_models", []),
            "entry_date": datetime.now(IST).isoformat(),
        })

    actual_invested = sum(h["allocation"] for h in holdings)
    # Truncation residue from int() quantity sizing → tracked as cash so
    # newly-created portfolio reports 0 P&L, not a fake tiny loss.
    truncation_residue = max(0.0, INITIAL_CAPITAL - actual_invested)

    # Best thesis from highest-vote model
    best_result = max(all_selections, key=lambda x: len(x[1].get("selections", [])))[1]

    portfolio_doc = {
        "type": strategy_type,
        "name": cfg["name"],
        "description": cfg["description"],
        "horizon": cfg["horizon"],
        "initial_capital": INITIAL_CAPITAL,
        "actual_invested": round(actual_invested, 2),
        "current_value": round(INITIAL_CAPITAL, 2),
        "holdings_value": round(actual_invested, 2),
        "cash_balance": round(truncation_residue, 2),
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "total_pnl": 0,
        "total_pnl_pct": 0,
        "holdings": holdings,
        "status": "active",
        "created_at": datetime.now(IST).isoformat(),
        "last_analyzed": datetime.now(IST).isoformat(),
        "last_rebalanced": None,
        "portfolio_thesis": best_result.get("portfolio_thesis", ""),
        "risk_assessment": best_result.get("risk_assessment", ""),
        "sector_allocation": best_result.get("sector_allocation", ""),
        "data_quality_note": best_result.get("data_quality_note", ""),
        "construction_log": {
            "pipeline": "hardened_v3",
            "universe_size": len(universe),
            "screened_candidates": len(candidates),
            "deep_enriched": len(shortlist),
            "guidance_stocks": len(guidance_data),
            "models_used": [n for n, r in model_results.items() if "error" not in r],
            "consensus_multi_vote": len(multi_vote),
            "sector_enforcement": True,
            "volatility_sizing": True,
            "data_validated": True,
            "constructed_at": datetime.now(IST).isoformat(),
        },
    }

    await db.portfolios.update_one(
        {"type": strategy_type},
        {"$set": portfolio_doc},
        upsert=True,
    )

    logger.info(f"PORTFOLIO [{strategy_type}]: Constructed with {len(holdings)} stocks, ₹{actual_invested:,.0f} invested (consensus: {len(multi_vote)} multi-vote)")
    return {"status": "constructed", "type": strategy_type, "holdings": len(holdings), "invested": actual_invested}


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE UPDATE & REBALANCING (Hardened)
# ═══════════════════════════════════════════════════════════════════════════════

async def update_portfolio_prices(db, strategy_type: str):
    """Fetch current prices and update portfolio P&L."""
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
            pass

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
    """Evaluate whether a portfolio needs rebalancing using God Mode with full data."""
    from services.full_market_scanner import get_nse_universe
    from services.intelligence_engine import _call_llm_in_thread

    import asyncio

    portfolio = await db.portfolios.find_one({"type": strategy_type}, {"_id": 0})
    if not portfolio or portfolio.get("status") != "active":
        return {"action": "SKIP", "reason": "Portfolio not active"}

    cfg = PORTFOLIO_STRATEGIES[strategy_type]
    holdings = portfolio.get("holdings", [])

    # ══════════════════════════════════════════════════════════════════════════
    # HARDENING: Programmatic stop-loss check BEFORE consulting LLMs
    # ══════════════════════════════════════════════════════════════════════════
    STOP_LOSS_PCT = -8.0   # Hard stop-loss
    TARGET_HIT_PCT = 20.0  # Auto-take-profit threshold
    auto_removes = []
    for h in holdings:
        pnl_pct = h.get("pnl_pct", 0) or 0
        if pnl_pct <= STOP_LOSS_PCT:
            auto_removes.append({"symbol": h["symbol"], "reason": f"STOP-LOSS breached ({pnl_pct:.1f}% < {STOP_LOSS_PCT}%)", "pnl_pct": pnl_pct})
            logger.info(f"REBALANCE [{strategy_type}]: Auto-stop {h['symbol']} at {pnl_pct:.1f}%")
        elif pnl_pct >= TARGET_HIT_PCT:
            # Check if momentum fading (RSI > 75 or declining trend)
            auto_removes.append({"symbol": h["symbol"], "reason": f"TARGET HIT ({pnl_pct:.1f}% > {TARGET_HIT_PCT}%), consider profit booking", "pnl_pct": pnl_pct})
            logger.info(f"REBALANCE [{strategy_type}]: Auto-target {h['symbol']} at {pnl_pct:.1f}%")

    # Build current holdings summary with detailed data
    holdings_text = ""
    winners = 0
    losers = 0
    for h in holdings:
        pnl_label = f"+{h['pnl_pct']:.1f}%" if h.get("pnl_pct", 0) >= 0 else f"{h['pnl_pct']:.1f}%"
        holdings_text += (
            f"  {h['symbol']} ({h.get('sector','')}) | Entry: ₹{h['entry_price']:.2f} | "
            f"Current: ₹{h.get('current_price', h['entry_price']):.2f} | P&L: {pnl_label} | "
            f"Weight: {h.get('weight',10):.1f}% | Qty: {h['quantity']}\n"
            f"    Rationale at entry: {h.get('rationale','')[:100]}\n"
            f"    Risk flag: {h.get('risk_flag','None noted')}\n"
        )
        if h.get("pnl_pct", 0) > 0:
            winners += 1
        elif h.get("pnl_pct", 0) < 0:
            losers += 1

    # Get guidance filings for current holdings
    held_tickers = [h["symbol"] for h in holdings]
    holdings_guidance = await _fetch_guidance_for_stocks(db, held_tickers)
    holdings_filings_text = ""
    for sym, filings in holdings_guidance.items():
        clean = sym.replace(".NS", "")
        holdings_filings_text += f"\n  {clean}:\n{_build_filing_context(filings)}\n"
    if not holdings_filings_text:
        holdings_filings_text = "No recent BSE filings found for current holdings."

    # Get market candidates for potential replacements
    universe = get_nse_universe()
    candidates_context = "No replacement candidates available."
    if universe:
        candidates = _advanced_screener(universe, strategy_type)[:20]
        held_syms = {h["symbol"] for h in holdings}
        candidates = [c for c in candidates if c["symbol"] not in held_syms][:10]
        if candidates:
            replacement_shortlist = _deep_enrich(candidates, max_shortlist=8)
            if replacement_shortlist:
                replacement_guidance = await _fetch_guidance_for_stocks(db, [s["symbol"] for s in replacement_shortlist])
                candidates_context = _build_hardened_context(replacement_shortlist, replacement_guidance)

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
        holdings_filings=holdings_filings_text,
    )

    user_text = (
        f"Evaluate {cfg['name']} portfolio for rebalancing.\n"
        f"All data below is REAL. Only recommend changes with STRONG evidence.\n\n"
        f"Return ONLY valid JSON."
    )

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"action": "ERROR", "reason": "LLM key not configured"}

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

    if rebalance_votes >= 2:
        best = max(
            [a for a in all_analyses if a.get("action") == "REBALANCE"],
            key=lambda x: x.get("confidence", 0)
        )
        changes = best.get("changes", [])
        if changes:
            await _execute_rebalance(db, strategy_type, portfolio, changes, best, model_names, results)
            return {"action": "REBALANCE", "changes": len(changes), "analysis": best.get("analysis_summary", "")}

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
    """Execute the rebalancing — swap stocks, realize P&L, track cash.

    Accounting model:
      - actual_invested stays as the ORIGINAL capital basis (immutable).
      - realized_pnl accumulates (cp - ep) * qty on exits.
      - cash_balance holds truncation leftovers / unreinvested proceeds.
    """
    # Hard rule: rebalance swaps only during safe market hours
    from utils.market_hours import is_market_safe
    ok, reason = await is_market_safe(db)
    if not ok:
        logger.info(f"REBALANCE [{strategy_type}]: skipped — {reason}")
        return

    import yfinance as yf

    holdings = portfolio.get("holdings", [])
    holdings_map = {h["symbol"]: h for h in holdings}
    cash_balance = float(portfolio.get("cash_balance", 0) or 0)
    realized_pnl_total = float(portfolio.get("realized_pnl", 0) or 0)
    executed_changes = []

    for change in changes[:2]:
        outgoing_info = change.get("outgoing", {})
        incoming_info = change.get("incoming", {})

        out_sym = outgoing_info.get("symbol", "")
        in_sym = incoming_info.get("symbol", "")

        if not out_sym or not in_sym:
            continue

        out_holding = holdings_map.get(out_sym)
        if not out_holding:
            continue

        in_price = incoming_info.get("entry_price", 0)
        if not in_price:
            try:
                ticker = yf.Ticker(in_sym)
                in_price = float(getattr(ticker.fast_info, "last_price", 0))
            except Exception:
                continue

        if in_price <= 0:
            continue

        out_cp = float(out_holding.get("current_price", out_holding["entry_price"]))
        out_ep = float(out_holding["entry_price"])
        out_qty = out_holding["quantity"]

        # Realize P&L on the sell
        out_pnl = (out_cp - out_ep) * out_qty
        out_pnl_pct = ((out_cp - out_ep) / out_ep * 100) if out_ep > 0 else 0
        proceeds = out_cp * out_qty
        realized_pnl_total += out_pnl

        # Deploy proceeds + any existing cash into the new buy
        budget = proceeds + cash_balance
        new_qty = int(budget / in_price)
        if new_qty < 1:
            new_qty = 1
        buy_cost = new_qty * in_price
        cash_balance = budget - buy_cost  # leftover truncation stays as cash

        executed_changes.append({
            "type": "SWAP",
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
                "type": "OUT",
                "symbol": out_sym,
                "name": out_holding.get("name", ""),
                "exit_price": round(out_cp, 2),
                "entry_price": round(out_ep, 2),
                "quantity": out_qty,
                "proceeds": round(proceeds, 2),
                "pnl": round(out_pnl, 2),
                "pnl_pct": round(out_pnl_pct, 2),
                "realized_pnl": round(out_pnl, 2),
                "realized_pnl_pct": round(out_pnl_pct, 2),
                "rationale": outgoing_info.get("rationale", ""),
                "held_since": out_holding.get("entry_date", ""),
            },
        })

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
            "risk_flag": "",
            "entry_date": datetime.now(IST).isoformat(),
        })
        # Keep map in sync for subsequent changes
        holdings_map = {h["symbol"]: h for h in holdings}

    if executed_changes:
        holdings_value = sum(h.get("current_price", h["entry_price"]) * h["quantity"] for h in holdings)
        current_value = holdings_value + cash_balance
        initial_capital = float(portfolio.get("initial_capital", INITIAL_CAPITAL) or INITIAL_CAPITAL)
        unrealized_pnl = sum(
            (h.get("current_price", h["entry_price"]) - h["entry_price"]) * h["quantity"]
            for h in holdings
        )
        # HONEST P&L: current value vs committed capital
        total_pnl = current_value - initial_capital
        total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

        await db.portfolios.update_one(
            {"type": strategy_type},
            {"$set": {
                "holdings": holdings,
                "cash_balance": round(cash_balance, 2),
                "realized_pnl": round(realized_pnl_total, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "current_value": round(current_value, 2),
                "holdings_value": round(holdings_value, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round(total_pnl_pct, 2),
                "last_rebalanced": datetime.now(IST).isoformat(),
            }}
        )

        # Flattened changes list for XIRR/audit (one IN + one OUT per swap)
        flat_changes = []
        for ec in executed_changes:
            flat_changes.append(ec["outgoing"])
            flat_changes.append({
                "type": "IN",
                "symbol": ec["incoming"]["symbol"],
                "name": ec["incoming"]["name"],
                "entry_price": ec["incoming"]["entry_price"],
                "quantity": ec["incoming"]["quantity"],
                "rationale": ec["incoming"]["rationale"],
            })

        await db.portfolio_rebalance_log.insert_one({
            "portfolio_type": strategy_type,
            "timestamp": datetime.now(IST).isoformat(),
            "action": "REBALANCE",
            "analysis_summary": analysis.get("analysis_summary", ""),
            "confidence": analysis.get("confidence", 0),
            "swaps": executed_changes,
            "changes": flat_changes,
            "portfolio_value_before": portfolio.get("current_value", 0),
            "portfolio_value_after": round(current_value, 2),
            "realized_pnl_delta": round(
                sum(ec["outgoing"]["realized_pnl"] for ec in executed_changes), 2
            ),
        })

        logger.info(
            f"REBALANCE [{strategy_type}]: {len(executed_changes)} swaps, "
            f"realized ₹{sum(ec['outgoing']['realized_pnl'] for ec in executed_changes):,.0f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# DB ACCESS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_all_portfolios(db):
    portfolios = await db.portfolios.find({}, {"_id": 0}).to_list(length=10)
    return portfolios


async def get_portfolio(db, strategy_type: str):
    return await db.portfolios.find_one({"type": strategy_type}, {"_id": 0})


async def get_rebalance_log(db, strategy_type: str = None, limit: int = 20):
    query = {}
    if strategy_type:
        query["portfolio_type"] = strategy_type
    logs = await db.portfolio_rebalance_log.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return logs


async def get_portfolio_overview(db):
    portfolios = await get_all_portfolios(db)

    total_capital = 0
    total_invested = 0
    total_value = 0
    total_realized = 0
    total_unrealized = 0
    total_cash = 0
    active = 0

    portfolio_summaries = []
    for p in portfolios:
        cap = float(p.get("initial_capital", INITIAL_CAPITAL) or INITIAL_CAPITAL)
        inv = float(p.get("actual_invested", cap) or cap)
        val = float(p.get("current_value", inv) or inv)
        realized = float(p.get("realized_pnl", 0) or 0)
        cash = float(p.get("cash_balance", 0) or 0)

        holdings = p.get("holdings", [])
        # Unrealized = MTM of current holdings vs their cost basis (notional)
        unrealized = sum(
            (float(h.get("current_price", h.get("entry_price", 0)) or 0) -
             float(h.get("entry_price", 0) or 0)) * h.get("quantity", 0)
            for h in holdings
        )
        # PMS Total Return = Realized + Unrealized
        total_return = realized + unrealized
        total_return_pct = (total_return / cap * 100) if cap > 0 else 0
        # NAV delta: what the portfolio page shows as "value change from capital"
        # In healthy PMS with cash always redeployed: NAV delta == Total Return.
        # For damaged portfolios (cash leaked historically): NAV delta < Total Return.
        nav_delta = val - cap

        total_capital += cap
        total_invested += inv
        total_value += val
        total_realized += realized
        total_unrealized += unrealized
        total_cash += cash
        if p.get("status") == "active":
            active += 1

        winners = sum(1 for h in holdings if h.get("pnl_pct", 0) > 0)
        losers = sum(1 for h in holdings if h.get("pnl_pct", 0) < 0)

        portfolio_summaries.append({
            "type": p.get("type"),
            "name": p.get("name"),
            "status": p.get("status"),
            "capital": round(cap, 2),
            "invested": round(inv, 2),
            "current_value": round(val, 2),
            "cash_balance": round(cash, 2),
            "realized_pnl": round(realized, 2),
            "unrealized_pnl": round(unrealized, 2),
            # total_pnl = PMS Total Return (realized + unrealized)
            "total_pnl": round(total_return, 2),
            "total_pnl_pct": round(total_return_pct, 2),
            "nav_delta": round(nav_delta, 2),
            "holdings_count": len(holdings),
            "winners": winners,
            "losers": losers,
            "created_at": p.get("created_at"),
            "last_analyzed": p.get("last_analyzed"),
            "last_rebalanced": p.get("last_rebalanced"),
        })

    existing_types = {p.get("type") for p in portfolios}
    pending = [t for t in PORTFOLIO_STRATEGIES if t not in existing_types]

    # Aggregate PMS metrics
    agg_total_return = total_realized + total_unrealized
    agg_total_return_pct = (agg_total_return / total_capital * 100) if total_capital > 0 else 0

    return {
        "total_capital": round(total_capital, 2),
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_cash_balance": round(total_cash, 2),
        "total_realized_pnl": round(total_realized, 2),
        "total_unrealized_pnl": round(total_unrealized, 2),
        "total_pnl": round(agg_total_return, 2),
        "total_pnl_pct": round(agg_total_return_pct, 2),
        "nav_delta": round(total_value - total_capital, 2),
        "active_portfolios": active,
        "pending_construction": len(pending),
        "pending_types": pending,
        "portfolios": portfolio_summaries,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS DAEMON
# ═══════════════════════════════════════════════════════════════════════════════

def start_portfolio_daemon(mongo_url: str, db_name: str):
    """
    Background daemon:
    1. On startup: construct any missing portfolios
    2. After market close (4 PM IST): update prices and evaluate rebalancing
    3. Continuous operation without human intervention
    """
    import asyncio as _aio
    from motor.motor_asyncio import AsyncIOMotorClient

    def _daemon_loop():
        logger.info("PORTFOLIO DAEMON: Started — Autonomous Mode (Hardened Pipeline v3)")
        time.sleep(60)

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
                loop.run_until_complete(
                    db.portfolios.delete_many({"status": {"$in": ["constructing", "error"]}})
                )
                missing = [t for t in PORTFOLIO_STRATEGIES if t not in existing]

                if missing:
                    strategy = missing[0]
                    logger.info(f"PORTFOLIO DAEMON: Constructing '{strategy}' with hardened v3 pipeline...")
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
                            loop.run_until_complete(db.portfolios.delete_one({"type": strategy}))
                    except Exception as e:
                        import traceback
                        logger.error(f"PORTFOLIO DAEMON: Construction failed for {strategy}: {e}\n{traceback.format_exc()}")
                        loop.run_until_complete(db.portfolios.delete_one({"type": strategy}))

                    client.close()
                    try:
                        loop.run_until_complete(loop.shutdown_default_executor())
                    except Exception:
                        pass
                    loop.close()
                    time.sleep(60)
                    continue

                # Phase 2: Update prices during/after market hours
                now = datetime.now(IST)
                hour = now.hour

                if 9 <= hour <= 16:
                    for strategy_type in PORTFOLIO_STRATEGIES:
                        try:
                            loop.run_until_complete(update_portfolio_prices(db, strategy_type))
                        except Exception as e:
                            logger.debug(f"PORTFOLIO DAEMON: Price update failed for {strategy_type}: {e}")
                        time.sleep(5)

                # Phase 3: After market close (4 PM - 6 PM IST): evaluate rebalancing
                if 16 <= hour <= 18:
                    today_str = now.strftime("%Y-%m-%d")
                    for strategy_type in PORTFOLIO_STRATEGIES:
                        last_log = loop.run_until_complete(
                            db.portfolio_rebalance_log.find_one(
                                {"portfolio_type": strategy_type, "timestamp": {"$regex": today_str}},
                                {"_id": 0}
                            )
                        )
                        if last_log:
                            continue

                        logger.info(f"PORTFOLIO DAEMON: Evaluating rebalance for '{strategy_type}' (hardened)...")
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

            now = datetime.now(IST)
            if 9 <= now.hour <= 18:
                time.sleep(300)
            else:
                time.sleep(1800)

    t = threading.Thread(target=_daemon_loop, daemon=True)
    t.start()
    logger.info("PORTFOLIO DAEMON: Thread launched — Autonomous Mode")

"""
Intelligence Engine - Multi-input AI signal generation.
Feeds ALL raw data (25+ technical indicators, 30+ fundamentals, OHLCV, news, sentiment, market regime)
plus learning context to the LLM for holistic signal generation.

Phase 4: Massively expanded context with full indicator suite.
"""
import os
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SIGNAL_SCHEMA_PROMPT = """You are the Bharat Market Intel Agent (BMIA), a Tier-1 Quant Analyst for Indian markets.

You receive an EXTREMELY comprehensive data packet with 25+ technical indicators and 30+ fundamental metrics.
You must analyze EVERY data point provided and generate a high-conviction, actionable trade signal.

ANALYSIS FRAMEWORK (weighted):
  Technical Analysis (40%):
  - Trend: MA regime (golden/death cross, price vs all MAs), ADX strength/direction, Ichimoku cloud signal
  - Momentum: RSI zone + divergence, Stochastic crossover + zone, MACD crossover + histogram, ROC direction, Williams %R, CCI
  - Volatility: Bollinger Bands (%B, squeeze, bandwidth), ATR% (high/medium/low)
  - Volume: OBV trend (accumulation/distribution), VSA signal (climactic buying/selling), volume trend (increasing/decreasing)
  - Structure: Fibonacci support/resistance, Pivot Points (S/R levels), 52W high/low proximity, consolidation detection
  - Price Action: candlestick patterns in last 5 bars, 20d/50d trend

  Fundamental Analysis (40%):
  - Valuation: P/E (trailing + forward), PEG, P/B, P/S, EV/EBITDA, EV/Revenue, Graham intrinsic value vs price
  - Profitability: ROE, ROA, profit/operating/gross margins
  - Growth: revenue growth, earnings growth, quarterly growth trend
  - Balance Sheet: debt/equity, debt/EBITDA, current ratio, quick ratio, net cash position
  - Cash Flow: FCF, operating cashflow, FCF yield
  - Ownership: insider %, institutional %, short ratio, float shares
  - Dividend: yield, payout ratio
  - Risk: beta
  - Quarterly Trend: last 4 quarters revenue + net income trajectory

  Sentiment Analysis (20%):
  - News: recent headlines with source, sentiment score (-1 to +1), keywords
  - Crowd sentiment label (Bullish/Bearish/Neutral)
  - Keyword triggers (positive/negative catalysts)

IMPORTANT RULES:
1. NEVER fabricate data. Only reference numbers from the provided context. Always cite indicator names and their values.
2. Your signal MUST be actionable with specific prices.
3. Risk/reward ratio should be at least 1:2 for BUY signals.
4. Always include what would INVALIDATE your thesis.
5. Learn from past mistakes provided in the learning context.
6. Be honest about uncertainty - lower confidence if data conflicts.
7. When indicators conflict (e.g., RSI oversold but ADX trending down), explicitly discuss the conflict.
8. Reference SPECIFIC numbers: "RSI at 32 indicates oversold" not just "RSI is oversold".
9. Consider Indian market context: SEBI regulations, FII/DII flows if relevant.
10. GUARDRAILS: Entry price must be within 3% of current price. Stop loss must be within 8% of entry. Targets must be reasonable (not >30% for swing trades).

Return ONLY valid JSON matching this exact schema:
{
  "action": "BUY" | "SELL" | "HOLD" | "AVOID",
  "timeframe": "INTRADAY" | "SWING" | "POSITIONAL",
  "horizon_days": <int 1-90>,
  "entry": {
    "type": "market" | "limit",
    "price": <float>,
    "rationale": "<why this entry, cite specific levels>"
  },
  "targets": [
    {"price": <float>, "probability": <float 0-1>, "label": "Target 1"},
    {"price": <float>, "probability": <float 0-1>, "label": "Target 2"}
  ],
  "stop_loss": {
    "price": <float>,
    "type": "hard" | "trailing",
    "rationale": "<why this stop, cite specific support/level>"
  },
  "confidence": <int 0-100>,
  "key_theses": ["<thesis 1 with specific data reference>", "<thesis 2>", "<thesis 3>"],
  "invalidators": ["<what would prove this wrong 1>", "<what would prove this wrong 2>"],
  "risk_reward_ratio": "<e.g. 1:2.5>",
  "position_sizing_hint": "<e.g. Risk 0.5-1% of capital>",
  "sector_context": "<how sector is performing>",
  "technical_summary": "<2-3 sentences summarizing all technical signals>",
  "fundamental_summary": "<2-3 sentences summarizing fundamental health>",
  "sentiment_summary": "<1-2 sentences on sentiment>",
  "detailed_reasoning": "<3-5 paragraph deep analysis covering technical, fundamental, and sentiment factors with specific indicator references>"
}"""


BATCH_RANKING_PROMPT = """You are the Bharat Market Intel Agent (BMIA), a Tier-1 Quant Analyst for Indian markets.

You receive summary data for multiple stocks. Analyze each stock comprehensively and rank them by investment attractiveness.

For each stock, you must evaluate:
- Technical setup (trend, momentum, volume, structure)
- Fundamental health (valuation, growth, profitability, balance sheet)
- Risk profile (volatility, debt, beta)

Return ONLY valid JSON matching this exact schema:
{
  "rankings": [
    {
      "symbol": "<symbol>",
      "rank": <int>,
      "ai_score": <int 0-100>,
      "action": "BUY" | "SELL" | "HOLD" | "AVOID",
      "conviction": "HIGH" | "MEDIUM" | "LOW",
      "rationale": "<2-3 sentence explanation citing specific metrics>",
      "key_strength": "<single most bullish factor>",
      "key_risk": "<single most bearish factor>"
    }
  ]
}

Rules:
1. Rank from most attractive (rank 1) to least attractive.
2. NEVER fabricate data. Only reference numbers from the provided context.
3. Score 0-100 where: 80+ = Strong Buy, 60-80 = Buy, 40-60 = Hold, 20-40 = Reduce, <20 = Avoid.
4. Be specific in rationale: cite P/E, RSI, growth rates, etc.
5. Consider Indian market context."""


def _safe_fmt(val, decimals=2, suffix=""):
    """Safely format a value for display in context."""
    if val is None:
        return "N/A"
    try:
        if isinstance(val, bool):
            return "Yes" if val else "No"
        if isinstance(val, (int, float)):
            formatted = round(float(val), decimals)
            return f"{formatted}{suffix}"
        return str(val)
    except Exception:
        return "N/A"


def _fmt_large(val):
    """Format large numbers (market cap, revenue, etc.)."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e12:
            return f"{val/1e12:.2f}T"
        elif abs(val) >= 1e9:
            return f"{val/1e9:.2f}B"
        elif abs(val) >= 1e7:
            return f"{val/1e7:.2f}Cr"
        elif abs(val) >= 1e5:
            return f"{val/1e5:.2f}L"
        else:
            return f"{val:,.0f}"
    except Exception:
        return "N/A"


def build_full_context(symbol: str, raw_data: dict, learning_context: dict = None) -> str:
    """Build a massive, structured text context from ALL available data."""
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
    parts = []
    parts.append(f"{'='*60}")
    parts.append(f"  SYMBOL: {clean_symbol} ({symbol})")
    parts.append(f"  Analysis timestamp: {datetime.now().isoformat()}")
    parts.append(f"{'='*60}")

    # ── PRICE DATA ──
    md = raw_data.get("market_data", {})
    parts.append(f"\n{'─'*40}")
    parts.append("  SECTION 1: PRICE DATA")
    parts.append(f"{'─'*40}")
    parts.append(f"Current Price: {_safe_fmt(md.get('latest', {}).get('close'))}")
    parts.append(f"Day Change: {_safe_fmt(md.get('change'))} ({_safe_fmt(md.get('change_pct'), suffix='%')})")
    parts.append(f"Data Points: {md.get('data_points', 'N/A')}")

    ohlcv = raw_data.get("chart_data", {}).get("ohlcv", [])
    if ohlcv and len(ohlcv) >= 5:
        parts.append("\nLast 5 days OHLCV:")
        for d in ohlcv[-5:]:
            parts.append(f"  {d['time']}: O={_safe_fmt(d['open'])} H={_safe_fmt(d['high'])} L={_safe_fmt(d['low'])} C={_safe_fmt(d['close'])} V={_fmt_large(d['volume'])}")

    # ── TECHNICAL INDICATORS (25+) ──
    tech = raw_data.get("technical", {})
    if tech and not tech.get("error"):
        parts.append(f"\n{'─'*40}")
        parts.append("  SECTION 2: TECHNICAL INDICATORS (25+ INDICATORS)")
        parts.append(f"{'─'*40}")

        # RSI
        rsi = tech.get("rsi", {})
        parts.append("\n[RSI (14)]")
        parts.append(f"  Current: {_safe_fmt(rsi.get('current'))}")
        rsi_zone = "Overbought" if (rsi.get('current') or 50) > 70 else "Oversold" if (rsi.get('current') or 50) < 30 else "Neutral"
        parts.append(f"  Zone: {rsi_zone}")

        # MACD
        macd = tech.get("macd", {})
        parts.append("\n[MACD (12, 26, 9)]")
        parts.append(f"  Line: {_safe_fmt(macd.get('line'), 4)}")
        parts.append(f"  Signal: {_safe_fmt(macd.get('signal'), 4)}")
        parts.append(f"  Histogram: {_safe_fmt(macd.get('histogram'), 4)}")
        parts.append(f"  Crossover: {macd.get('crossover', 'N/A')}")

        # Bollinger Bands
        bb = tech.get("bollinger", {})
        parts.append("\n[Bollinger Bands (20, 2)]")
        parts.append(f"  Upper: {_safe_fmt(bb.get('upper'))}")
        parts.append(f"  Middle (SMA20): {_safe_fmt(bb.get('middle'))}")
        parts.append(f"  Lower: {_safe_fmt(bb.get('lower'))}")
        parts.append(f"  Bandwidth: {_safe_fmt(bb.get('bandwidth'), suffix='%')}")
        parts.append(f"  %B: {_safe_fmt(bb.get('percent_b'), 4)}")
        parts.append(f"  Bollinger Squeeze: {_safe_fmt(bb.get('squeeze'))}")
        parts.append(f"  Price Position: {bb.get('position', 'N/A')}")

        # ADX
        adx = tech.get("adx", {})
        parts.append("\n[ADX (14)]")
        parts.append(f"  ADX: {_safe_fmt(adx.get('adx'))}")
        parts.append(f"  +DI: {_safe_fmt(adx.get('plus_di'))}")
        parts.append(f"  -DI: {_safe_fmt(adx.get('minus_di'))}")
        parts.append(f"  Trend Strength: {adx.get('trend_strength', 'N/A')}")
        parts.append(f"  Direction: {adx.get('direction', 'N/A')}")

        # Stochastic
        stoch = tech.get("stochastic", {})
        parts.append("\n[Stochastic Oscillator (14, 3)]")
        parts.append(f"  %K: {_safe_fmt(stoch.get('k'))}")
        parts.append(f"  %D: {_safe_fmt(stoch.get('d'))}")
        parts.append(f"  Zone: {stoch.get('zone', 'N/A')}")
        parts.append(f"  Crossover: {stoch.get('crossover', 'N/A')}")

        # ATR
        atr = tech.get("atr", {})
        parts.append("\n[ATR (14)]")
        parts.append(f"  ATR: {_safe_fmt(atr.get('atr'))}")
        parts.append(f"  ATR%: {_safe_fmt(atr.get('atr_pct'), suffix='%')}")
        parts.append(f"  Volatility: {atr.get('volatility', 'N/A')}")

        # OBV
        obv = tech.get("obv", {})
        parts.append("\n[On-Balance Volume (OBV)]")
        parts.append(f"  OBV: {_fmt_large(obv.get('obv'))}")
        parts.append(f"  OBV SMA20: {_fmt_large(obv.get('obv_sma20'))}")
        parts.append(f"  Trend: {obv.get('trend', 'N/A')}")

        # Williams %R
        wr = tech.get("williams_r", {})
        parts.append("\n[Williams %R (14)]")
        parts.append(f"  Value: {_safe_fmt(wr.get('value'))}")
        parts.append(f"  Zone: {wr.get('zone', 'N/A')}")

        # CCI
        cci = tech.get("cci", {})
        parts.append("\n[CCI (20)]")
        parts.append(f"  Value: {_safe_fmt(cci.get('value'))}")
        parts.append(f"  Zone: {cci.get('zone', 'N/A')}")

        # ROC
        roc = tech.get("roc", {})
        parts.append("\n[Rate of Change (12)]")
        parts.append(f"  ROC: {_safe_fmt(roc.get('value'), suffix='%')}")
        parts.append(f"  Direction: {roc.get('direction', 'N/A')}")

        # Ichimoku
        ich = tech.get("ichimoku", {})
        parts.append("\n[Ichimoku Cloud]")
        parts.append(f"  Tenkan-sen (9): {_safe_fmt(ich.get('tenkan'))}")
        parts.append(f"  Kijun-sen (26): {_safe_fmt(ich.get('kijun'))}")
        parts.append(f"  Senkou Span A: {_safe_fmt(ich.get('senkou_a'))}")
        parts.append(f"  Senkou Span B: {_safe_fmt(ich.get('senkou_b'))}")
        parts.append(f"  Cloud Signal: {ich.get('cloud_signal', 'N/A')}")
        parts.append(f"  TK Cross: {ich.get('tk_cross', 'N/A')}")
        parts.append(f"  Cloud Thickness: {_safe_fmt(ich.get('cloud_thickness'))}")

        # Fibonacci
        fib = tech.get("fibonacci", {})
        if fib.get("levels"):
            parts.append("\n[Fibonacci Retracement Levels]")
            for level, price in fib["levels"].items():
                parts.append(f"  {level}: {_safe_fmt(price)}")
            parts.append(f"  Nearest Support: {_safe_fmt(fib.get('nearest_support'))}")
            parts.append(f"  Nearest Resistance: {_safe_fmt(fib.get('nearest_resistance'))}")

        # Pivot Points
        pp = tech.get("pivot_points", {})
        parts.append("\n[Pivot Points]")
        parts.append(f"  PP: {_safe_fmt(pp.get('pp'))}")
        parts.append(f"  R1: {_safe_fmt(pp.get('r1'))}  R2: {_safe_fmt(pp.get('r2'))}  R3: {_safe_fmt(pp.get('r3'))}")
        parts.append(f"  S1: {_safe_fmt(pp.get('s1'))}  S2: {_safe_fmt(pp.get('s2'))}  S3: {_safe_fmt(pp.get('s3'))}")

        # VSA
        vsa = tech.get("vsa", {})
        parts.append("\n[Volume Spread Analysis]")
        parts.append(f"  Volume Ratio: {_safe_fmt(vsa.get('vol_ratio'))}x average")
        parts.append(f"  Spread: {_safe_fmt(vsa.get('spread'))}")
        parts.append(f"  Signal: {vsa.get('signal', 'N/A')}")
        parts.append(f"  Volume Trend (5d vs 20d): {vsa.get('vol_trend', 'N/A')}")
        parts.append(f"  Avg Volume (20d): {_fmt_large(vsa.get('avg_vol_20d'))}")

        # Breakout Detection
        bk = tech.get("breakout", {})
        parts.append("\n[Breakout Detection]")
        parts.append(f"  52-Week High: {_safe_fmt(bk.get('high_52w'))}")
        parts.append(f"  52-Week Low: {_safe_fmt(bk.get('low_52w'))}")
        parts.append(f"  Distance from 52W High: {_safe_fmt(bk.get('distance_from_high_pct'), suffix='%')}")
        parts.append(f"  Distance from 52W Low: {_safe_fmt(bk.get('distance_from_low_pct'), suffix='%')}")
        parts.append(f"  Near 52W High: {_safe_fmt(bk.get('near_52w_high'))}")
        parts.append(f"  Near 52W Low: {_safe_fmt(bk.get('near_52w_low'))}")
        parts.append(f"  Volume Confirmation: {_safe_fmt(bk.get('volume_confirmation'))}")
        parts.append(f"  30d Consolidation: {_safe_fmt(bk.get('consolidation_30d'))}")
        parts.append(f"  30d Range: {_safe_fmt(bk.get('range_30d_pct'), suffix='%')}")

        # Moving Averages
        ma = tech.get("moving_averages", {})
        parts.append("\n[Moving Averages Suite]")
        for p in [5, 10, 20, 50, 100, 200]:
            sma_key = f"sma_{p}"
            ema_key = f"ema_{p}"
            if sma_key in ma:
                parts.append(f"  SMA{p}: {_safe_fmt(ma[sma_key])}  |  EMA{p}: {_safe_fmt(ma.get(ema_key))}")
        parts.append(f"  Golden Cross (SMA50>SMA200): {_safe_fmt(ma.get('golden_cross'))}")
        parts.append(f"  Death Cross (SMA50<SMA200): {_safe_fmt(ma.get('death_cross'))}")
        parts.append(f"  Price Above All Key MAs: {_safe_fmt(ma.get('above_all_ma'))}")

        # Price Action
        pa = tech.get("price_action", {})
        parts.append("\n[Price Action]")
        parts.append(f"  20-Day Trend: {pa.get('trend_20d', 'N/A')}")
        parts.append(f"  50-Day Trend: {pa.get('trend_50d', 'N/A')}")
        parts.append(f"  Daily Change: {_safe_fmt(pa.get('daily_change_pct'), suffix='%')}")

    # ── FUNDAMENTALS (30+) ──
    fund = raw_data.get("fundamental", {})
    if fund and not fund.get("error"):
        parts.append(f"\n{'─'*40}")
        parts.append("  SECTION 3: FUNDAMENTAL DATA (30+ METRICS)")
        parts.append(f"{'─'*40}")

        parts.append("\n[Company Info]")
        parts.append(f"  Sector: {fund.get('sector', 'N/A')}")
        parts.append(f"  Industry: {fund.get('industry', 'N/A')}")
        parts.append(f"  Market Cap: {_fmt_large(fund.get('market_cap'))}")
        parts.append(f"  Enterprise Value: {_fmt_large(fund.get('enterprise_value'))}")
        parts.append(f"  Employees: {_fmt_large(fund.get('full_time_employees'))}")

        parts.append("\n[Valuation Ratios]")
        parts.append(f"  P/E (Trailing): {_safe_fmt(fund.get('pe_ratio'))}")
        parts.append(f"  P/E (Forward): {_safe_fmt(fund.get('forward_pe'))}")
        parts.append(f"  PEG Ratio: {_safe_fmt(fund.get('peg_ratio'))}")
        parts.append(f"  Price/Sales: {_safe_fmt(fund.get('price_to_sales'))}")
        parts.append(f"  Price/Book: {_safe_fmt(fund.get('price_to_book'))}")
        parts.append(f"  EV/EBITDA: {_safe_fmt(fund.get('ev_to_ebitda'))}")
        parts.append(f"  EV/Revenue: {_safe_fmt(fund.get('ev_to_revenue'))}")

        parts.append("\n[Graham Intrinsic Value]")
        parts.append(f"  Graham Value: {_safe_fmt(fund.get('graham_value'))}")
        parts.append(f"  Current Price: {_safe_fmt(fund.get('current_price'))}")
        parts.append(f"  Valuation Status: {fund.get('valuation', 'N/A')}")

        parts.append("\n[Profitability]")
        parts.append(f"  Gross Margin: {_safe_fmt(fund.get('gross_margin'), suffix='%')}")
        parts.append(f"  Operating Margin: {_safe_fmt(fund.get('operating_margin'), suffix='%')}")
        parts.append(f"  Profit Margin: {_safe_fmt(fund.get('profit_margin'), suffix='%')}")
        parts.append(f"  ROE: {_safe_fmt(fund.get('roe'), suffix='%')}")
        parts.append(f"  ROA: {_safe_fmt(fund.get('roa'), suffix='%')}")

        parts.append("\n[Growth]")
        parts.append(f"  Revenue Growth: {_safe_fmt(fund.get('revenue_growth'), suffix='%')}")
        parts.append(f"  Earnings Growth: {_safe_fmt(fund.get('earnings_growth'), suffix='%')}")
        parts.append(f"  Quarterly Earnings Growth: {_safe_fmt(fund.get('earnings_quarterly_growth'), suffix='%')}")

        parts.append("\n[Balance Sheet & Liquidity]")
        parts.append(f"  Debt/Equity: {_safe_fmt(fund.get('debt_to_equity'))}")
        parts.append(f"  Debt/EBITDA: {_safe_fmt(fund.get('debt_to_ebitda'))}")
        parts.append(f"  Current Ratio: {_safe_fmt(fund.get('current_ratio'))}")
        parts.append(f"  Quick Ratio: {_safe_fmt(fund.get('quick_ratio'))}")
        parts.append(f"  Total Debt: {_fmt_large(fund.get('total_debt'))}")
        parts.append(f"  Total Cash: {_fmt_large(fund.get('total_cash'))}")
        parts.append(f"  Net Cash: {_fmt_large(fund.get('net_cash'))}")

        parts.append("\n[Cash Flow]")
        parts.append(f"  Free Cash Flow: {_fmt_large(fund.get('free_cashflow'))}")
        parts.append(f"  Operating Cash Flow: {_fmt_large(fund.get('operating_cashflow'))}")
        parts.append(f"  FCF Yield: {_safe_fmt(fund.get('fcf_yield'), suffix='%')}")

        parts.append("\n[Per Share Data]")
        parts.append(f"  EPS (Trailing): {_safe_fmt(fund.get('eps'))}")
        parts.append(f"  EPS (Forward): {_safe_fmt(fund.get('forward_eps'))}")
        parts.append(f"  Book Value/Share: {_safe_fmt(fund.get('bvps'))}")
        parts.append(f"  Revenue/Share: {_safe_fmt(fund.get('revenue_per_share'))}")

        parts.append("\n[Dividends]")
        parts.append(f"  Dividend Yield: {_safe_fmt(fund.get('dividend_yield'), suffix='%')}")
        parts.append(f"  Dividend Rate: {_safe_fmt(fund.get('dividend_rate'))}")
        parts.append(f"  Payout Ratio: {_safe_fmt(fund.get('payout_ratio'), suffix='%')}")

        parts.append("\n[Risk & Ownership]")
        parts.append(f"  Beta: {_safe_fmt(fund.get('beta'))}")
        parts.append(f"  Insider Holdings: {_safe_fmt(fund.get('held_pct_insiders'), suffix='%')}")
        parts.append(f"  Institutional Holdings: {_safe_fmt(fund.get('held_pct_institutions'), suffix='%')}")
        parts.append(f"  Short Ratio: {_safe_fmt(fund.get('short_ratio'))}")
        parts.append(f"  52-Week High: {_safe_fmt(fund.get('fifty_two_week_high'))}")
        parts.append(f"  52-Week Low: {_safe_fmt(fund.get('fifty_two_week_low'))}")

        # Quarterly data
        qr = fund.get("quarterly_revenue", [])
        qe = fund.get("quarterly_earnings", [])
        if qr:
            parts.append("\n[Quarterly Revenue (last 4)]")
            for q in qr:
                parts.append(f"  {q.get('quarter', '?')}: {_fmt_large(q.get('revenue'))}")
        if qe:
            parts.append("\n[Quarterly Net Income (last 4)]")
            for q in qe:
                parts.append(f"  {q.get('quarter', '?')}: {_fmt_large(q.get('net_income'))}")

    # ── NEWS & SENTIMENT ──
    if raw_data.get("news"):
        headlines = raw_data["news"].get("headlines", [])
        parts.append(f"\n{'─'*40}")
        parts.append(f"  SECTION 4: NEWS ({len(headlines)} headlines)")
        parts.append(f"{'─'*40}")
        for i, h in enumerate(headlines[:10]):
            parts.append(f"  {i+1}. [{h.get('publisher', '?')}] {h.get('title', '')}")

    if raw_data.get("sentiment"):
        sent = raw_data["sentiment"]
        parts.append(f"\n{'─'*40}")
        parts.append("  SECTION 5: SENTIMENT ANALYSIS")
        parts.append(f"{'─'*40}")
        parts.append(f"  Overall Score: {_safe_fmt(sent.get('score'))} (scale: -1 bearish to +1 bullish)")
        parts.append(f"  Label: {sent.get('label', 'N/A')}")
        parts.append(f"  Rationale: {sent.get('rationale', 'N/A')}")
        parts.append(f"  Keywords: {', '.join(sent.get('keywords', []))}")

    # ── LEARNING CONTEXT ──
    if learning_context and learning_context.get("lessons"):
        parts.append(f"\n{'─'*40}")
        parts.append("  SECTION 6: LEARNING FROM PAST SIGNALS")
        parts.append(f"{'─'*40}")
        parts.append(f"  Total past signals: {learning_context.get('total_signals', 0)}")
        parts.append(f"  Win rate: {learning_context.get('win_rate', 'N/A')}%")
        parts.append(f"  Avg return: {learning_context.get('avg_return', 'N/A')}%")
        for lesson in learning_context.get("lessons", [])[:5]:
            parts.append(f"  LESSON: {lesson}")
        if learning_context.get("recent_mistakes"):
            parts.append("\n  Recent mistakes to avoid:")
            for mistake in learning_context["recent_mistakes"][:3]:
                parts.append(f"  MISTAKE: {mistake}")

    return "\n".join(parts)


def build_batch_context(stocks_data: list) -> str:
    """Build compact summaries for batch ranking."""
    parts = []
    parts.append(f"BATCH ANALYSIS - {len(stocks_data)} stocks")
    parts.append(f"Timestamp: {datetime.now().isoformat()}\n")

    for i, stock in enumerate(stocks_data):
        sym = stock.get("symbol", "?")
        clean = sym.replace(".NS", "").replace(".BO", "").replace("=F", "")
        parts.append(f"{'─'*30}")
        parts.append(f"Stock {i+1}: {clean} ({sym})")
        parts.append(f"{'─'*30}")

        # Price
        md = stock.get("market_data", {})
        parts.append(f"Price: {_safe_fmt(md.get('price'))} | Change: {_safe_fmt(md.get('change_pct'), suffix='%')}")

        # Key technicals
        tech = stock.get("technical", {})
        rsi = tech.get("rsi", {})
        macd = tech.get("macd", {})
        bb = tech.get("bollinger", {})
        adx = tech.get("adx", {})
        stoch = tech.get("stochastic", {})
        atr = tech.get("atr", {})
        obv = tech.get("obv", {})
        ma = tech.get("moving_averages", {})
        bk = tech.get("breakout", {})
        ich = tech.get("ichimoku", {})
        pa = tech.get("price_action", {})

        parts.append(f"RSI: {_safe_fmt(rsi.get('current'))} | MACD Hist: {_safe_fmt(macd.get('histogram'), 4)} ({macd.get('crossover', '?')})")
        parts.append(f"Bollinger: %B={_safe_fmt(bb.get('percent_b'), 3)}, Squeeze={_safe_fmt(bb.get('squeeze'))}, Pos={bb.get('position', '?')}")
        parts.append(f"ADX: {_safe_fmt(adx.get('adx'))} ({adx.get('trend_strength', '?')}, {adx.get('direction', '?')})")
        parts.append(f"Stochastic: %K={_safe_fmt(stoch.get('k'))}, Zone={stoch.get('zone', '?')}, Cross={stoch.get('crossover', '?')}")
        parts.append(f"ATR%: {_safe_fmt(atr.get('atr_pct'), suffix='%')} ({atr.get('volatility', '?')})")
        parts.append(f"OBV Trend: {obv.get('trend', '?')} | VSA: {tech.get('vsa', {}).get('signal', '?')}")
        parts.append(f"MAs: Above All={_safe_fmt(ma.get('above_all_ma'))}, Golden Cross={_safe_fmt(ma.get('golden_cross'))}")
        parts.append(f"Ichimoku: {ich.get('cloud_signal', '?')}, TK Cross={ich.get('tk_cross', '?')}")
        parts.append(f"52W: High dist={_safe_fmt(bk.get('distance_from_high_pct'), suffix='%')}, Consolidation={_safe_fmt(bk.get('consolidation_30d'))}")
        parts.append(f"Trend: 20d={pa.get('trend_20d', '?')}, 50d={pa.get('trend_50d', '?')}")

        # Key fundamentals
        fund = stock.get("fundamental", {})
        parts.append(f"P/E: {_safe_fmt(fund.get('pe_ratio'))} | Fwd P/E: {_safe_fmt(fund.get('forward_pe'))} | PEG: {_safe_fmt(fund.get('peg_ratio'))}")
        parts.append(f"P/B: {_safe_fmt(fund.get('price_to_book'))} | EV/EBITDA: {_safe_fmt(fund.get('ev_to_ebitda'))}")
        parts.append(f"ROE: {_safe_fmt(fund.get('roe'), suffix='%')} | Profit Margin: {_safe_fmt(fund.get('profit_margin'), suffix='%')}")
        parts.append(f"Rev Growth: {_safe_fmt(fund.get('revenue_growth'), suffix='%')} | Earnings Growth: {_safe_fmt(fund.get('earnings_growth'), suffix='%')}")
        parts.append(f"D/E: {_safe_fmt(fund.get('debt_to_equity'))} | Current Ratio: {_safe_fmt(fund.get('current_ratio'))}")
        parts.append(f"FCF Yield: {_safe_fmt(fund.get('fcf_yield'), suffix='%')} | Beta: {_safe_fmt(fund.get('beta'))}")
        parts.append(f"Graham Value: {_safe_fmt(fund.get('graham_value'))} | Valuation: {fund.get('valuation', '?')}")
        parts.append(f"Div Yield: {_safe_fmt(fund.get('dividend_yield'), suffix='%')} | Insider%: {_safe_fmt(fund.get('held_pct_insiders'), suffix='%')}")
        parts.append("")

    return "\n".join(parts)


async def generate_ai_signal(symbol: str, raw_data: dict, learning_context: dict = None, provider: str = "openai"):
    """Generate an AI-driven trade signal using multi-input intelligence with expanded indicators."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM API key not configured."}

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        model_map = {
            "openai": ("openai", "gpt-4.1"),
            "claude": ("anthropic", "claude-sonnet-4-5-20250929"),
            "gemini": ("gemini", "gemini-2.5-flash"),
        }
        provider_name, model_name = model_map.get(provider, ("openai", "gpt-4.1"))

        clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")

        # Build the massive context
        full_context = build_full_context(symbol, raw_data, learning_context)

        chat = LlmChat(
            api_key=api_key,
            session_id=f"signal-{symbol}-{datetime.now().isoformat()}",
            system_message=SIGNAL_SCHEMA_PROMPT
        )
        chat.with_model(provider_name, model_name)

        user_msg = UserMessage(
            text=f"Generate a trade signal for {clean_symbol} based on this comprehensive data:\n\n{full_context}\n\nReturn ONLY valid JSON."
        )

        response = await chat.send_message(user_msg)

        # Parse response
        try:
            resp_text = response.strip()
            if resp_text.startswith("```"):
                resp_text = resp_text.split("```")[1]
                if resp_text.startswith("json"):
                    resp_text = resp_text[4:]
            signal_data = json.loads(resp_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                signal_data = json.loads(json_match.group())
            else:
                return {"error": "Failed to parse AI signal response", "raw": response[:500]}

        # Validate and sanitize
        signal_data["symbol"] = symbol
        signal_data["provider"] = provider_name
        signal_data["model"] = model_name
        signal_data["generated_at"] = datetime.now().isoformat()

        # Ensure required fields exist
        if "action" not in signal_data:
            signal_data["action"] = "HOLD"
        if "confidence" not in signal_data:
            signal_data["confidence"] = 50
        if "targets" not in signal_data:
            signal_data["targets"] = []
        if "stop_loss" not in signal_data:
            signal_data["stop_loss"] = {"price": 0, "type": "hard", "rationale": "Not specified"}

        return signal_data

    except Exception as e:
        logger.error(f"Intelligence engine error for {symbol}: {e}")
        return {"error": str(e)}


async def generate_batch_ranking(stocks_data: list, provider: str = "openai"):
    """Generate AI-powered batch ranking for multiple stocks."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM API key not configured."}

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        model_map = {
            "openai": ("openai", "gpt-4.1"),
            "claude": ("anthropic", "claude-sonnet-4-5-20250929"),
            "gemini": ("gemini", "gemini-2.5-flash"),
        }
        provider_name, model_name = model_map.get(provider, ("openai", "gpt-4.1"))

        batch_context = build_batch_context(stocks_data)

        chat = LlmChat(
            api_key=api_key,
            session_id=f"batch-{datetime.now().isoformat()}",
            system_message=BATCH_RANKING_PROMPT
        )
        chat.with_model(provider_name, model_name)

        user_msg = UserMessage(
            text=f"Rank these {len(stocks_data)} stocks by investment attractiveness:\n\n{batch_context}\n\nReturn ONLY valid JSON."
        )

        response = await chat.send_message(user_msg)

        # Parse response
        try:
            resp_text = response.strip()
            if resp_text.startswith("```"):
                resp_text = resp_text.split("```")[1]
                if resp_text.startswith("json"):
                    resp_text = resp_text[4:]
            ranking_data = json.loads(resp_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                ranking_data = json.loads(json_match.group())
            else:
                return {"error": "Failed to parse AI batch ranking", "raw": response[:500]}

        ranking_data["provider"] = provider_name
        ranking_data["model"] = model_name
        ranking_data["generated_at"] = datetime.now().isoformat()

        return ranking_data

    except Exception as e:
        logger.error(f"Batch ranking error: {e}")
        return {"error": str(e)}



GOD_MODE_SYNTHESIS_PROMPT = """You are the Meta-Analyst of the Bharat Market Intel Agent (BMIA).

You receive 3 independent trade signal analyses for the SAME stock from 3 different AI models (OpenAI GPT-4.1, Anthropic Claude Sonnet, Google Gemini Flash).

Your job is to SYNTHESIZE these into a single, distilled consensus signal that is MORE robust than any individual analysis.

SYNTHESIS RULES:
1. If all 3 agree on action → HIGH agreement. Use the consensus with highest conviction.
2. If 2 agree, 1 dissents → MEDIUM agreement. Go with the majority but note the dissent.
3. If all 3 disagree → LOW agreement. Default to the most conservative position (HOLD/AVOID).
4. For entry/target/stop prices: use the MEDIAN of the 3 values.
5. For confidence: average the 3 confidences, then adjust down if agreement is LOW.
6. Explicitly state where the models DISAGREE and WHY the disagreement matters.
7. Never fabricate data. Reference specific values from the input signals.
8. The distilled signal must be actionable and specific.

Return ONLY valid JSON:
{
  "action": "BUY" | "SELL" | "HOLD" | "AVOID",
  "timeframe": "INTRADAY" | "SWING" | "POSITIONAL",
  "horizon_days": <int>,
  "entry": {"type": "market" | "limit", "price": <float>, "rationale": "<merged rationale>"},
  "targets": [{"price": <float>, "probability": <float>, "label": "Target 1"}, ...],
  "stop_loss": {"price": <float>, "type": "hard" | "trailing", "rationale": "<merged rationale>"},
  "confidence": <int 0-100>,
  "risk_reward_ratio": "<e.g. 1:2.5>",
  "key_theses": ["<thesis 1>", "<thesis 2>", "<thesis 3>"],
  "invalidators": ["<invalidator 1>", "<invalidator 2>"],
  "technical_summary": "<consensus technical view>",
  "fundamental_summary": "<consensus fundamental view>",
  "sentiment_summary": "<consensus sentiment>",
  "detailed_reasoning": "<3-5 paragraphs synthesizing all 3 models>",
  "agreement_level": "HIGH" | "MEDIUM" | "LOW",
  "model_votes": {
    "openai": {"action": "...", "confidence": <int>, "key_thesis": "..."},
    "claude": {"action": "...", "confidence": <int>, "key_thesis": "..."},
    "gemini": {"action": "...", "confidence": <int>, "key_thesis": "..."}
  },
  "disagreements": ["<where models disagree and why>"],
  "consensus_edge": "<what makes this distilled view better than any single model>"
}"""


GOD_MODE_BATCH_SYNTHESIS_PROMPT = """You are the Meta-Analyst of BMIA.

You receive 3 independent batch stock rankings from 3 AI models. Synthesize into one consensus ranking.

Rules:
1. Average ranks across models, weighted by model conviction.
2. If all 3 say BUY for a stock → HIGH conviction BUY.
3. Final output should prioritize BUY calls.
4. Note disagreements.

Return ONLY valid JSON:
{
  "rankings": [
    {
      "symbol": "<symbol>",
      "rank": <int>,
      "ai_score": <int 0-100>,
      "action": "BUY" | "SELL" | "HOLD" | "AVOID",
      "conviction": "HIGH" | "MEDIUM" | "LOW",
      "agreement_level": "HIGH" | "MEDIUM" | "LOW",
      "rationale": "<distilled from all 3 models>",
      "key_strength": "<consensus strength>",
      "key_risk": "<consensus risk>",
      "model_votes": {"openai": "<action>", "claude": "<action>", "gemini": "<action>"}
    }
  ]
}"""


async def _call_llm(api_key, provider_name, model_name, system_msg, user_text, session_suffix=""):
    """Helper to call a single LLM and parse JSON response."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=api_key,
            session_id=f"god-{provider_name}-{session_suffix}-{datetime.now().isoformat()}",
            system_message=system_msg,
        )
        chat.with_model(provider_name, model_name)
        response = await chat.send_message(UserMessage(text=user_text))

        resp_text = response.strip()
        if resp_text.startswith("```"):
            resp_text = resp_text.split("```")[1]
            if resp_text.startswith("json"):
                resp_text = resp_text[4:]
        return json.loads(resp_text)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", response if "response" in dir() else "")
        if json_match:
            return json.loads(json_match.group())
        return {"error": f"JSON parse fail from {provider_name}", "raw": (response if "response" in dir() else "")[:300]}
    except Exception as e:
        return {"error": f"{provider_name} failed: {str(e)}"}


async def generate_god_mode_signal(symbol: str, raw_data: dict, learning_context: dict = None):
    """
    GOD MODE: Send to ALL 3 LLMs in parallel, then synthesize consensus.
    Returns a distilled signal with agreement metrics.
    """
    import asyncio

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM API key not configured."}

    clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
    full_context = build_full_context(symbol, raw_data, learning_context)

    models = [
        ("openai", "gpt-4.1"),
        ("anthropic", "claude-sonnet-4-5-20250929"),
        ("gemini", "gemini-2.5-flash"),
    ]

    user_text = f"Generate a trade signal for {clean_symbol} based on this comprehensive data:\n\n{full_context}\n\nReturn ONLY valid JSON."

    # Stage 1: Parallel calls to all 3 LLMs
    logger.info(f"GOD MODE: Sending {clean_symbol} to {len(models)} LLMs in parallel...")
    tasks = [
        _call_llm(api_key, prov, model, SIGNAL_SCHEMA_PROMPT, user_text, clean_symbol)
        for prov, model in models
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    signals = {}
    provider_names = ["openai", "claude", "gemini"]
    for i, (prov_name, result) in enumerate(zip(provider_names, results)):
        if isinstance(result, Exception):
            signals[prov_name] = {"error": str(result)}
        elif isinstance(result, dict):
            signals[prov_name] = result
        else:
            signals[prov_name] = {"error": "Unknown result type"}

    valid_signals = {k: v for k, v in signals.items() if "error" not in v}

    if len(valid_signals) == 0:
        return {"error": "All 3 LLMs failed", "details": signals}

    if len(valid_signals) == 1:
        # Only one succeeded - return it with low agreement
        single = list(valid_signals.values())[0]
        single["god_mode"] = True
        single["agreement_level"] = "LOW"
        single["model_votes"] = {k: {"action": v.get("action", "ERROR"), "confidence": v.get("confidence", 0)} for k, v in signals.items()}
        single["models_succeeded"] = list(valid_signals.keys())
        return single

    # Stage 2: Synthesize consensus
    logger.info(f"GOD MODE: Synthesizing {len(valid_signals)} signals for {clean_symbol}...")

    synthesis_input = f"Stock: {clean_symbol}\n\n"
    for prov_name, sig in signals.items():
        if "error" in sig:
            synthesis_input += f"=== {prov_name.upper()} ===\nFAILED: {sig['error']}\n\n"
        else:
            synthesis_input += f"=== {prov_name.upper()} ===\n{json.dumps(sig, indent=2, default=str)[:3000]}\n\n"

    synthesis_input += "\nSynthesize these into a single consensus signal. Return ONLY valid JSON."

    consensus = await _call_llm(
        api_key, "openai", "gpt-4.1",
        GOD_MODE_SYNTHESIS_PROMPT, synthesis_input, f"synth-{clean_symbol}"
    )

    if "error" in consensus:
        # Synthesis failed - return best individual signal
        best = max(valid_signals.values(), key=lambda x: x.get("confidence", 0))
        best["god_mode"] = True
        best["agreement_level"] = "MEDIUM"
        best["synthesis_error"] = consensus.get("error")
        best["model_votes"] = {k: {"action": v.get("action", "ERROR"), "confidence": v.get("confidence", 0)} for k, v in signals.items()}
        return best

    consensus["god_mode"] = True
    consensus["symbol"] = symbol
    consensus["models_succeeded"] = list(valid_signals.keys())
    consensus["generated_at"] = datetime.now().isoformat()

    # Ensure model_votes exists
    if "model_votes" not in consensus:
        consensus["model_votes"] = {}
        for prov_name, sig in signals.items():
            consensus["model_votes"][prov_name] = {
                "action": sig.get("action", "ERROR") if "error" not in sig else "FAILED",
                "confidence": sig.get("confidence", 0) if "error" not in sig else 0,
                "key_thesis": (sig.get("key_theses", [""])[0] if sig.get("key_theses") else "") if "error" not in sig else sig.get("error", ""),
            }

    return consensus


async def generate_god_mode_batch_ranking(stocks_data: list):
    """
    GOD MODE batch: All 3 LLMs rank stocks independently, then synthesize consensus.
    """
    import asyncio

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM API key not configured."}

    batch_context = build_batch_context(stocks_data)

    models = [
        ("openai", "gpt-4.1"),
        ("anthropic", "claude-sonnet-4-5-20250929"),
        ("gemini", "gemini-2.5-flash"),
    ]

    user_text = f"Rank these {len(stocks_data)} stocks by investment attractiveness (prioritize BUY candidates):\n\n{batch_context}\n\nReturn ONLY valid JSON."

    # Parallel ranking from all 3 LLMs
    logger.info(f"GOD MODE BATCH: Sending {len(stocks_data)} stocks to {len(models)} LLMs...")
    tasks = [
        _call_llm(api_key, prov, model, BATCH_RANKING_PROMPT, user_text, "batch")
        for prov, model in models
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    rankings = {}
    provider_names = ["openai", "claude", "gemini"]
    for prov_name, result in zip(provider_names, results):
        if isinstance(result, Exception):
            rankings[prov_name] = {"error": str(result)}
        elif isinstance(result, dict):
            rankings[prov_name] = result
        else:
            rankings[prov_name] = {"error": "Unknown"}

    valid_rankings = {k: v for k, v in rankings.items() if "error" not in v and "rankings" in v}

    if len(valid_rankings) == 0:
        return {"error": "All LLMs failed for batch", "details": rankings}

    # Synthesize
    logger.info(f"GOD MODE BATCH: Synthesizing {len(valid_rankings)} ranking sets...")
    synthesis_input = "Multiple AI model rankings for the same stocks:\n\n"
    for prov_name, rank_data in rankings.items():
        if "error" in rank_data:
            synthesis_input += f"=== {prov_name.upper()} ===\nFAILED: {rank_data['error']}\n\n"
        else:
            synthesis_input += f"=== {prov_name.upper()} ===\n{json.dumps(rank_data.get('rankings', []), indent=1, default=str)[:3000]}\n\n"

    synthesis_input += "\nSynthesize into a single consensus ranking. Prioritize BUY calls. Return ONLY valid JSON."

    consensus = await _call_llm(
        api_key, "openai", "gpt-4.1",
        GOD_MODE_BATCH_SYNTHESIS_PROMPT, synthesis_input, "batch-synth"
    )

    if "error" in consensus:
        # Fallback to best individual ranking
        best = max(valid_rankings.values(), key=lambda v: len(v.get("rankings", [])))
        best["god_mode"] = True
        best["synthesis_error"] = consensus.get("error")
        return best

    consensus["god_mode"] = True
    consensus["models_succeeded"] = list(valid_rankings.keys())
    consensus["generated_at"] = datetime.now().isoformat()
    return consensus

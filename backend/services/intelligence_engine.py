"""
Intelligence Engine - Multi-input AI signal generation.
Feeds ALL raw data (OHLCV, indicators, fundamentals, news, sentiment, market regime)
plus learning context to the LLM for holistic signal generation.
"""
import os
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SIGNAL_SCHEMA_PROMPT = """You are the Bharat Market Intel Agent (BMIA), a Tier-1 Quant Analyst for Indian markets.

You must generate an actionable trade signal based on ALL the provided data. Analyze every dimension:
- Technical: trend, momentum (RSI, MACD), volume patterns (VSA), support/resistance, breakout status
- Fundamental: valuation (P/E vs peers, Graham value), growth, debt health, profitability
- Sentiment: news tone, keyword triggers, crowd sentiment
- Market regime: volatility, trend strength, sector rotation

IMPORTANT RULES:
1. NEVER fabricate data. Only reference numbers from the provided context.
2. Your signal MUST be actionable with specific prices.
3. Risk/reward ratio should be at least 1:2 for BUY signals.
4. Always include what would INVALIDATE your thesis.
5. Learn from past mistakes provided in the learning context.
6. Be honest about uncertainty - lower confidence if data conflicts.

Return ONLY valid JSON matching this exact schema:
{
  "action": "BUY" | "SELL" | "HOLD" | "AVOID",
  "timeframe": "INTRADAY" | "SWING" | "POSITIONAL",
  "horizon_days": <int 1-90>,
  "entry": {
    "type": "market" | "limit",
    "price": <float>,
    "rationale": "<why this entry>"
  },
  "targets": [
    {"price": <float>, "probability": <float 0-1>, "label": "Target 1"},
    {"price": <float>, "probability": <float 0-1>, "label": "Target 2"}
  ],
  "stop_loss": {
    "price": <float>,
    "type": "hard" | "trailing",
    "rationale": "<why this stop>"
  },
  "confidence": <int 0-100>,
  "key_theses": ["<thesis 1 with data reference>", "<thesis 2>", "<thesis 3>"],
  "invalidators": ["<what would prove this wrong 1>", "<what would prove this wrong 2>"],
  "risk_reward_ratio": "<e.g. 1:2.5>",
  "position_sizing_hint": "<e.g. Risk 0.5-1% of capital>",
  "sector_context": "<how sector is performing>",
  "detailed_reasoning": "<3-5 paragraph deep analysis covering technical, fundamental, and sentiment factors>"
}"""


async def generate_ai_signal(symbol: str, raw_data: dict, learning_context: dict = None, provider: str = "openai"):
    """Generate an AI-driven trade signal using multi-input intelligence."""
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

        # Build comprehensive data context
        context_parts = []
        context_parts.append(f"=== SYMBOL: {clean_symbol} ({symbol}) ===")
        context_parts.append(f"Analysis timestamp: {datetime.now().isoformat()}")

        # Market data
        if raw_data.get("market_data"):
            md = raw_data["market_data"]
            context_parts.append(f"\n--- PRICE DATA ---")
            context_parts.append(f"Current Price: {md.get('latest', {}).get('close', 'N/A')}")
            context_parts.append(f"Day Change: {md.get('change', 'N/A')} ({md.get('change_pct', 'N/A')}%)")
            context_parts.append(f"Data points: {md.get('data_points', 'N/A')}")
            # Recent OHLCV
            ohlcv = raw_data.get("chart_data", {}).get("ohlcv", [])
            if ohlcv and len(ohlcv) > 5:
                context_parts.append(f"Last 5 days OHLCV:")
                for d in ohlcv[-5:]:
                    context_parts.append(f"  {d['time']}: O={d['open']} H={d['high']} L={d['low']} C={d['close']} V={d['volume']}")

        # Technical analysis
        if raw_data.get("technical") and not raw_data["technical"].get("error"):
            tech = raw_data["technical"]
            context_parts.append(f"\n--- TECHNICAL INDICATORS ---")
            context_parts.append(f"RSI(14): {tech.get('rsi', {}).get('current', 'N/A')}")
            macd = tech.get("macd", {})
            context_parts.append(f"MACD Line: {macd.get('line', 'N/A')}, Signal: {macd.get('signal', 'N/A')}, Histogram: {macd.get('histogram', 'N/A')}")
            mas = tech.get("moving_averages", {})
            context_parts.append(f"Moving Averages: MA20={mas.get('ma_20', 'N/A')}, MA50={mas.get('ma_50', 'N/A')}, MA200={mas.get('ma_200', 'N/A')}")
            vsa = tech.get("vsa", {})
            context_parts.append(f"VSA: Signal={vsa.get('signal', 'N/A')}, Volume Ratio={vsa.get('vol_ratio', 'N/A')}, Spread={vsa.get('spread', 'N/A')}")
            breakout = tech.get("breakout", {})
            context_parts.append(f"Breakout: {breakout.get('is_breakout', False)}, 52W High={breakout.get('level', 'N/A')}, Distance={breakout.get('distance_pct', 'N/A')}%")
            context_parts.append(f"Technical Score (formula-based): {tech.get('technical_score', 'N/A')}/100")

        # Fundamentals
        if raw_data.get("fundamental"):
            fund = raw_data["fundamental"]
            context_parts.append(f"\n--- FUNDAMENTAL DATA ---")
            context_parts.append(f"P/E Ratio: {fund.get('pe_ratio', 'N/A')}")
            context_parts.append(f"Debt/Equity: {fund.get('debt_to_equity', 'N/A')}")
            context_parts.append(f"Revenue Growth: {fund.get('revenue_growth', 'N/A')}%")
            context_parts.append(f"EPS: {fund.get('eps', 'N/A')}, Book Value: {fund.get('bvps', 'N/A')}")
            context_parts.append(f"Graham Intrinsic Value: {fund.get('graham_value', 'N/A')}")
            context_parts.append(f"ROE: {fund.get('roe', 'N/A')}%, Profit Margin: {fund.get('profit_margin', 'N/A')}%")
            context_parts.append(f"Valuation: {fund.get('valuation', 'N/A')}")
            context_parts.append(f"Sector: {fund.get('sector', 'N/A')}, Industry: {fund.get('industry', 'N/A')}")
            context_parts.append(f"Fundamental Score (formula-based): {fund.get('fundamental_score', 'N/A')}/100")

        # News & Sentiment
        if raw_data.get("news"):
            headlines = raw_data["news"].get("headlines", [])
            context_parts.append(f"\n--- NEWS ({len(headlines)} headlines) ---")
            for i, h in enumerate(headlines[:8]):
                context_parts.append(f"  {i+1}. [{h.get('publisher', '?')}] {h.get('title', '')}")

        if raw_data.get("sentiment"):
            sent = raw_data["sentiment"]
            context_parts.append(f"\n--- SENTIMENT ANALYSIS ---")
            context_parts.append(f"Overall Score: {sent.get('score', 'N/A')} (scale: -1 bearish to +1 bullish)")
            context_parts.append(f"Label: {sent.get('label', 'N/A')}")
            context_parts.append(f"Rationale: {sent.get('rationale', 'N/A')}")
            context_parts.append(f"Keywords: {', '.join(sent.get('keywords', []))}")

        # Alpha Score
        if raw_data.get("alpha"):
            alpha = raw_data["alpha"]
            context_parts.append(f"\n--- ALPHA SCORE (formula-based) ---")
            context_parts.append(f"Alpha Score: {alpha.get('alpha_score', 'N/A')}")
            context_parts.append(f"Sharpe Ratio: {alpha.get('sharpe_ratio', 'N/A')}")
            context_parts.append(f"Momentum: {alpha.get('momentum', 'N/A')}")

        # Learning context
        if learning_context and learning_context.get("lessons"):
            context_parts.append(f"\n--- LEARNING FROM PAST SIGNALS ---")
            context_parts.append(f"Total past signals: {learning_context.get('total_signals', 0)}")
            context_parts.append(f"Win rate: {learning_context.get('win_rate', 'N/A')}%")
            context_parts.append(f"Avg return: {learning_context.get('avg_return', 'N/A')}%")
            for lesson in learning_context.get("lessons", [])[:5]:
                context_parts.append(f"  LESSON: {lesson}")
            if learning_context.get("recent_mistakes"):
                context_parts.append(f"\nRecent mistakes to avoid:")
                for mistake in learning_context["recent_mistakes"][:3]:
                    context_parts.append(f"  MISTAKE: {mistake}")

        full_context = "\n".join(context_parts)

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

"""6-agent Fund Management pipeline (BMIA-flavoured TradingAgents).

Hierarchy (executes top-to-bottom; analysts run in parallel):

  ANALYSTS (parallel)            RESEARCH (debate)        DECISION
    Fundamentals  ─┐                                       ┌── Trader
    Sentiment     ─┼──► Bull   ◄──debate──►  Bear  ───────►┤
    News          ─┤                                       └── Risk Manager ──► Fund Manager
    Technical     ─┘

All agents share Claude Sonnet 4.5 via emergentintegrations. Each agent
returns structured JSON so downstream agents can reason over it. Rationales
are kept under 250 words for UI density.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"


# ─── Common LLM helper ─────────────────────────────────────────────────────
async def _agent_call(role: str, system: str, user_text: str,
                      session_id: str) -> Dict[str, Any]:
    """Run one agent turn and parse the JSON response. Falls back to a
    structured error object on LLM failure so downstream agents don't crash."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY missing", "role": role}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=system,
        ).with_model(MODEL_PROVIDER, MODEL_NAME)
        resp = await chat.send_message(UserMessage(text=user_text[:8000]))
        raw = (resp or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"role": role, "rationale": raw[:1200], "verdict": "HOLD",
                    "confidence": 0.4, "_warning": "LLM did not return valid JSON"}
    except Exception as e:
        logger.warning(f"FUND agent {role} call failed: {e}")
        return {"role": role, "error": str(e)[:200]}


# ─── Analysts (parallel) ───────────────────────────────────────────────────
FUNDAMENTALS_SYS = """You are a top-tier Indian-equity fundamentals analyst.
Given a stock's fundamental metrics, output a STRICT JSON object:
{
 "verdict": "BULLISH|NEUTRAL|BEARISH",
 "confidence": 0.0-1.0,
 "key_strengths": ["..." , "..."],
 "key_weaknesses": ["..." , "..."],
 "rationale": "<= 200 words explaining the call, rooted in the metrics provided."
}
Be specific about Indian market norms (e.g. NIFTY 50 median P/E ~22, RoE >15% is good for non-banks)."""

SENTIMENT_SYS = """You are an Indian-equity sentiment analyst.
Given recent FII/DII flows, PCR, and market breadth indicators, output STRICT JSON:
{
 "verdict": "RISK_ON|NEUTRAL|RISK_OFF",
 "confidence": 0.0-1.0,
 "key_signals": ["...","..."],
 "rationale": "<= 200 words on what the flow & options data say about positioning RIGHT NOW."
}
Rule of thumb: PCR > 1 is bearish, FII net selling > ₹3000Cr/day is risk-off."""

NEWS_SYS = """You are an Indian-markets news analyst.
Given recent news headlines & summaries about a specific stock, output STRICT JSON:
{
 "verdict": "POSITIVE|NEUTRAL|NEGATIVE",
 "confidence": 0.0-1.0,
 "catalysts": ["..." , "..."],
 "risks": ["..." , "..."],
 "rationale": "<= 200 words connecting the headlines to potential price action."
}
If no news provided, set verdict=NEUTRAL and confidence=0.3."""

TECHNICAL_SYS = """You are an Indian-equity technical analyst.
Given OHLCV-derived indicators (RSI, SMAs, 52w levels, vol), output STRICT JSON:
{
 "verdict": "BULLISH|NEUTRAL|BEARISH",
 "confidence": 0.0-1.0,
 "support": <number>,
 "resistance": <number>,
 "trend": "uptrend|sideways|downtrend",
 "rationale": "<= 200 words. Focus on RSI extremes, golden/death cross, and proximity to 52w high/low."
}"""


async def analyst_fundamentals(symbol: str, fundamentals: Dict, sid: str):
    return await _agent_call(
        "fundamentals", FUNDAMENTALS_SYS,
        f"Symbol: {symbol}\nFundamentals: {json.dumps(fundamentals)}", sid,
    )

async def analyst_sentiment(symbol: str, sentiment: Dict, sid: str):
    return await _agent_call(
        "sentiment", SENTIMENT_SYS,
        f"Symbol: {symbol}\nMarket sentiment data: {json.dumps(sentiment, default=str)}", sid,
    )

async def analyst_news(symbol: str, news_items: list, sid: str):
    headlines = "\n".join(
        f"- [{n.get('published_at','')[:10]}] {n.get('title','')} — {n.get('summary','')[:160]}"
        for n in (news_items or [])[:10]
    ) or "(no recent news in BMIA feed)"
    return await _agent_call(
        "news", NEWS_SYS,
        f"Symbol: {symbol}\nRecent headlines:\n{headlines}", sid,
    )

async def analyst_technical(symbol: str, tech: Dict, sid: str):
    return await _agent_call(
        "technical", TECHNICAL_SYS,
        f"Symbol: {symbol}\nTechnical indicators: {json.dumps(tech)}", sid,
    )


# ─── Bull / Bear research debate ───────────────────────────────────────────
BULL_SYS = """You are the Bull Researcher in a buy-side investment committee.
Given the four analyst reports (fundamentals, sentiment, news, technical),
construct the strongest possible BUY thesis for this stock. Output STRICT JSON:
{
 "thesis": "<= 250 words, structured as: 1) primary bull case, 2) catalysts, 3) why current price is attractive",
 "key_drivers": ["...","..."],
 "target_horizon_months": 3-12,
 "conviction": 0.0-1.0
}
Be intellectually honest — if the data clearly says SELL, your conviction must be low (<0.3)."""

BEAR_SYS = """You are the Bear Researcher.
Given the same four analyst reports, construct the strongest possible AVOID/SHORT thesis. STRICT JSON:
{
 "thesis": "<= 250 words covering: 1) primary bear case, 2) downside risks, 3) why now is not the time to enter",
 "key_risks": ["...","..."],
 "target_horizon_months": 3-12,
 "conviction": 0.0-1.0
}
If data clearly says BUY, conviction must be low."""


async def researcher_bull(symbol: str, analysts: Dict, sid: str):
    return await _agent_call(
        "bull", BULL_SYS,
        f"Symbol: {symbol}\nAnalyst reports:\n{json.dumps(analysts, default=str)}", sid,
    )

async def researcher_bear(symbol: str, analysts: Dict, sid: str):
    return await _agent_call(
        "bear", BEAR_SYS,
        f"Symbol: {symbol}\nAnalyst reports:\n{json.dumps(analysts, default=str)}", sid,
    )


# ─── Trader: synthesises analysts + debate into an actionable plan ─────────
TRADER_SYS = """You are an Indian-markets trader. Given the analyst reports and
the bull/bear debate, propose ONE actionable trade idea. STRICT JSON:
{
 "action": "BUY|HOLD|SELL",
 "conviction": 0.0-1.0,
 "entry_price": <number or null>,
 "stop_loss": <number or null>,
 "target_price": <number or null>,
 "horizon_months": 1-24,
 "position_size_pct_of_portfolio": 0-15,
 "rationale": "<= 200 words tying together the strongest analyst signal + the winning side of the debate."
}
Rules: stop_loss must be <= 8% below entry for BUY; target_price must give >= 1.5:1 R:R."""


async def trader(symbol: str, analysts: Dict, debate: Dict, last_price: Optional[float], sid: str):
    return await _agent_call(
        "trader", TRADER_SYS,
        f"Symbol: {symbol}\nLast price: {last_price}\n"
        f"Analyst reports: {json.dumps(analysts, default=str)}\n"
        f"Debate: {json.dumps(debate, default=str)}", sid,
    )


# ─── Risk Manager: flags portfolio-level concerns ──────────────────────────
RISK_SYS = """You are the Risk Manager for a discretionary Indian-equity fund.
Given the trader's proposal and the user's current portfolio exposure, score the trade on:
{
 "concentration_risk": "LOW|MEDIUM|HIGH",
 "regulatory_risk": "LOW|MEDIUM|HIGH",
 "market_regime_fit": "GOOD|NEUTRAL|POOR",
 "approve": true|false,
 "max_position_size_pct": 0-15,
 "concerns": ["...","..."],
 "rationale": "<= 180 words."
}
Veto rules: if portfolio sector exposure for the trade's sector is > 35%, force approve=false.
If regulatory_hits include SEBI orders against this stock in the last 90 days, force approve=false."""


async def risk_manager(symbol: str, trade_proposal: Dict, portfolio: Dict,
                       compliance: Dict, sid: str):
    return await _agent_call(
        "risk", RISK_SYS,
        f"Symbol: {symbol}\nTrade proposal: {json.dumps(trade_proposal, default=str)}\n"
        f"Portfolio context: {json.dumps(portfolio, default=str)}\n"
        f"Regulatory check: {json.dumps(compliance, default=str)}", sid,
    )


# ─── Fund Manager: final verdict ───────────────────────────────────────────
FUND_MANAGER_SYS = """You are the Fund Manager — the final decision-maker on this trade.
Given EVERY upstream output (analysts, bull/bear debate, trader proposal, risk review),
deliver the final verdict. STRICT JSON:
{
 "final_verdict": "STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL",
 "confidence": 0.0-1.0,
 "headline": "one-sentence verdict with target",
 "approved_action": {
   "action": "BUY|HOLD|SELL",
   "entry_price": <number or null>,
   "stop_loss": <number or null>,
   "target_price": <number or null>,
   "horizon_months": 1-24,
   "max_position_size_pct": 0-15
 },
 "key_reasons": ["...","..."],
 "watch_outs": ["...","..."],
 "rationale": "<= 250 words explaining how you weighed each input. Be explicit about which agents you trusted most and why."
}
Rules: must respect risk_manager.approve and risk_manager.max_position_size_pct.
If the bull and bear conviction are within 0.15 of each other, force final_verdict=HOLD."""


async def fund_manager(symbol: str, all_outputs: Dict, sid: str):
    return await _agent_call(
        "fund_manager", FUND_MANAGER_SYS,
        f"Symbol: {symbol}\nAll upstream outputs:\n{json.dumps(all_outputs, default=str)}", sid,
    )

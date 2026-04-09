"""
AI Agent Service - LLM-powered market analysis chat
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def get_ai_analysis(symbol: str, analysis_data: dict, user_query: str = None, provider: str = "openai"):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM API key not configured."}
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        model_map = {
            "openai": ("openai", "gpt-4.1-mini"),
            "claude": ("anthropic", "claude-sonnet-4-5-20250929"),
            "gemini": ("gemini", "gemini-2.5-flash"),
        }
        provider_name, model_name = model_map.get(provider, ("openai", "gpt-4.1-mini"))
        
        clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
        
        context = json.dumps(analysis_data, indent=2, default=str)
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"agent-{symbol}-{datetime.now().isoformat()}",
            system_message="""You are the Bharat Market Intel Agent (BMIA), a Tier-1 Quant Analyst specializing in Indian markets (NSE/BSE/MCX).

You provide high-conviction investment analysis synthesizing Technical, Fundamental, and Sentiment data.

Rules:
1. Always reference actual data provided - never fabricate numbers.
2. Be specific about support/resistance levels, risk factors, and catalysts.
3. Structure your response with clear sections: Summary, Technical View, Fundamental View, Sentiment, Risk Factors.
4. End with a clear recommendation and risk disclaimer.
5. Use professional but accessible language.
6. If data is missing, explicitly state it rather than guessing.
7. Adhere to SEBI guidelines: always provide risk disclaimers."""
        )
        chat.with_model(provider_name, model_name)
        
        prompt = f"""Analyze {clean_symbol} based on this data:

{context}

{f'User question: {user_query}' if user_query else 'Provide a comprehensive analysis and recommendation.'}"""
        
        user_msg = UserMessage(text=prompt)
        response = await chat.send_message(user_msg)
        
        return {
            "response": response,
            "provider": provider_name,
            "model": model_name,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"AI agent error: {e}")
        return {"error": str(e)}

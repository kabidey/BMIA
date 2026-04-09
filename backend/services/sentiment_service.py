"""
Sentiment Analysis Service using LLM
"""
import os
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def analyze_sentiment(symbol: str, headlines: list):
    if not headlines:
        return {
            "score": 0,
            "sentiment_score_0_100": 50,
            "label": "Neutral",
            "rationale": "No headlines available for analysis.",
            "keywords": [],
            "per_headline": [],
        }
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY not set, using default sentiment")
        return {
            "score": 0,
            "sentiment_score_0_100": 50,
            "label": "Neutral",
            "rationale": "LLM API key not configured.",
            "keywords": [],
            "per_headline": [],
        }
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        headline_text = "\n".join([f"{i+1}. {h['title']}" for i, h in enumerate(headlines[:8])])
        clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"sentiment-{symbol}-{datetime.now().isoformat()}",
            system_message="""You are a financial sentiment analyst for Indian markets.
Analyze news headlines and return ONLY valid JSON with no extra text.
Format:
{
  "overall_score": <float -1 to 1>,
  "label": "<Bullish|Bearish|Neutral>",
  "rationale": "<2-3 sentence explanation>",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "per_headline": [{"index": 1, "score": <float -1 to 1>, "brief": "<short reason>"}]
}
Score: -1 = very bearish, 0 = neutral, 1 = very bullish."""
        )
        chat.with_model("openai", "gpt-4.1-mini")
        
        user_msg = UserMessage(
            text=f"Analyze these headlines for {clean_symbol} stock/commodity sentiment:\n\n{headline_text}"
        )
        
        response = await chat.send_message(user_msg)
        
        try:
            resp_text = response.strip()
            if resp_text.startswith("```"):
                resp_text = resp_text.split("```")[1]
                if resp_text.startswith("json"):
                    resp_text = resp_text[4:]
            sentiment_data = json.loads(resp_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                sentiment_data = json.loads(json_match.group())
            else:
                sentiment_data = {"overall_score": 0, "label": "Neutral", "rationale": response[:200], "keywords": [], "per_headline": []}
        
        score = float(sentiment_data.get("overall_score", sentiment_data.get("score", 0)))
        sentiment_score_0_100 = int((score + 1) * 50)
        
        return {
            "score": score,
            "sentiment_score_0_100": sentiment_score_0_100,
            "label": sentiment_data.get("label", "Neutral"),
            "rationale": sentiment_data.get("rationale", ""),
            "keywords": sentiment_data.get("keywords", []),
            "per_headline": sentiment_data.get("per_headline", []),
        }
    except Exception as e:
        logger.error(f"Sentiment analysis error for {symbol}: {e}")
        return {
            "score": 0,
            "sentiment_score_0_100": 50,
            "label": "Neutral",
            "rationale": f"Error: {str(e)}",
            "keywords": [],
            "per_headline": [],
        }

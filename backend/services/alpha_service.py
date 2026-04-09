"""
Alpha Score Computation Service
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


def compute_sharpe_ratio(returns_list, risk_free_rate=0.065):
    if not returns_list or len(returns_list) < 2:
        return None
    
    returns = np.array(returns_list)
    avg_return = np.mean(returns) * 252
    std_return = np.std(returns) * np.sqrt(252)
    
    if std_return == 0:
        return None
    
    return round((avg_return - risk_free_rate) / std_return, 4)


def compute_momentum(price_now, price_n, vol_ratio):
    if not price_n or price_n == 0:
        return None
    vol_ratio = max(vol_ratio, 0.01)
    return round((price_now - price_n) / (price_n * vol_ratio), 4)


def compute_alpha_score(technical_score, fundamental_score, sentiment_score):
    alpha = 0.4 * technical_score + 0.4 * fundamental_score + 0.2 * sentiment_score
    return round(alpha, 2)


def get_recommendation(alpha_score):
    if alpha_score > 85:
        return "STRONG BUY"
    elif alpha_score > 70:
        return "BUY"
    elif alpha_score > 60:
        return "ACCUMULATE"
    elif alpha_score >= 40:
        return "NEUTRAL"
    elif alpha_score >= 30:
        return "REDUCE"
    else:
        return "SELL/AVOID"


def get_recommendation_color(recommendation):
    colors = {
        "STRONG BUY": "#22c55e",
        "BUY": "#4ade80",
        "ACCUMULATE": "#86efac",
        "NEUTRAL": "#f59e0b",
        "REDUCE": "#f97316",
        "SELL/AVOID": "#ef4444",
    }
    return colors.get(recommendation, "#6b7280")


def full_alpha_computation(ohlcv_data, technical_score, fundamental_score, sentiment_score):
    alpha_score = compute_alpha_score(technical_score, fundamental_score, sentiment_score)
    recommendation = get_recommendation(alpha_score)
    
    sharpe = None
    momentum = None
    if ohlcv_data and len(ohlcv_data) > 20:
        closes = [d["close"] for d in ohlcv_data]
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        sharpe = compute_sharpe_ratio(returns)
        
        if len(closes) > 5:
            momentum = compute_momentum(closes[-1], closes[0], 1.0)
    
    return {
        "alpha_score": alpha_score,
        "recommendation": recommendation,
        "recommendation_color": get_recommendation_color(recommendation),
        "technical_score": technical_score,
        "fundamental_score": fundamental_score,
        "sentiment_score": sentiment_score,
        "sharpe_ratio": sharpe,
        "momentum": momentum,
        "weights": {"technical": 0.4, "fundamental": 0.4, "sentiment": 0.2},
        "disclaimer": "This is for educational purposes only. Not financial advice. Past performance does not guarantee future results. Invest at your own risk. Always consult a SEBI-registered financial advisor.",
    }

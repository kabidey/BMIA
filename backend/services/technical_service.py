"""
Technical Analysis Service - RSI, MACD, VSA, Breakout Detection
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


def _ema(data, period):
    alpha = 2 / (period + 1)
    result = np.zeros_like(data, dtype=float)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def calculate_rsi(close_prices, period=14):
    if len(close_prices) < period + 1:
        return None, []
    
    deltas = np.diff(close_prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    rsi_series = []
    for i in range(period, len(deltas)):
        avg_gain = np.mean(gains[max(0, i - period):i])
        avg_loss = np.mean(losses[max(0, i - period):i])
        rs = avg_gain / (avg_loss + 1e-10)
        rsi_val = 100 - (100 / (1 + rs))
        rsi_series.append(round(rsi_val, 2))
    
    current_rsi = rsi_series[-1] if rsi_series else None
    return current_rsi, rsi_series


def calculate_macd(close_prices, fast=12, slow=26, signal=9):
    if len(close_prices) < slow + signal:
        return None, None, None, [], [], []
    
    ema_fast = _ema(close_prices, fast)
    ema_slow = _ema(close_prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return (
        round(float(macd_line[-1]), 4),
        round(float(signal_line[-1]), 4),
        round(float(histogram[-1]), 4),
        [round(float(x), 4) for x in macd_line[slow:]],
        [round(float(x), 4) for x in signal_line[slow:]],
        [round(float(x), 4) for x in histogram[slow:]],
    )


def calculate_moving_averages(close_prices):
    result = {}
    for period in [20, 50, 200]:
        if len(close_prices) >= period:
            result[f"ma_{period}"] = round(float(np.mean(close_prices[-period:])), 2)
        else:
            result[f"ma_{period}"] = None
    return result


def analyze_vsa(close_prices, volumes):
    if len(close_prices) < 20 or len(volumes) < 20:
        return {"vol_ratio": None, "spread": None, "signal": "Insufficient data"}
    
    avg_vol_20 = np.mean(volumes[-20:])
    current_vol = volumes[-1]
    vol_ratio = round(current_vol / (avg_vol_20 + 1e-10), 2)
    
    spread = round(float(close_prices[-1] - close_prices[-2]), 2)
    
    signal = "Neutral"
    if vol_ratio > 1.5 and spread > 0:
        signal = "Bullish Volume"
    elif vol_ratio > 1.5 and spread < 0:
        signal = "Bearish Volume"
    elif vol_ratio < 0.5:
        signal = "Low Volume - Caution"
    
    return {"vol_ratio": vol_ratio, "spread": spread, "signal": signal}


def detect_breakout(high_prices, close_prices):
    if len(high_prices) < 50:
        return {"is_breakout": False, "level": None}
    
    high_52w = float(np.max(high_prices[-252:])) if len(high_prices) >= 252 else float(np.max(high_prices))
    current = float(close_prices[-1])
    
    is_breakout = current >= high_52w * 0.98
    return {
        "is_breakout": is_breakout,
        "level": round(high_52w, 2),
        "distance_pct": round((current / high_52w - 1) * 100, 2)
    }


def compute_technical_score(rsi, macd_histogram, above_ma, vol_signal, is_breakout):
    score = 50
    
    if rsi is not None:
        if 50 < rsi < 70:
            score += 15
        elif rsi >= 70:
            score += 5
        elif rsi < 30:
            score -= 15
        elif 30 <= rsi <= 50:
            score -= 5
    
    if macd_histogram is not None:
        if macd_histogram > 0:
            score += 15
        else:
            score -= 10
    
    if above_ma:
        score += 10
    
    if vol_signal == "Bullish Volume":
        score += 10
    elif vol_signal == "Bearish Volume":
        score -= 10
    
    if is_breakout:
        score += 10
    
    return max(0, min(100, score))


def full_technical_analysis(ohlcv_data):
    if not ohlcv_data or len(ohlcv_data) < 30:
        return {"error": "Insufficient data for technical analysis"}
    
    close = np.array([d["close"] for d in ohlcv_data])
    high = np.array([d["high"] for d in ohlcv_data])
    low = np.array([d["low"] for d in ohlcv_data])
    volume = np.array([d["volume"] for d in ohlcv_data])
    times = [d["time"] for d in ohlcv_data]
    
    rsi_val, rsi_series = calculate_rsi(close)
    macd_line, macd_signal, macd_hist, macd_series, signal_series, hist_series = calculate_macd(close)
    mas = calculate_moving_averages(close)
    vsa = analyze_vsa(close, volume)
    breakout = detect_breakout(high, close)
    
    above_ma = close[-1] > mas.get("ma_20", 0) if mas.get("ma_20") else False
    
    tech_score = compute_technical_score(
        rsi_val, macd_hist, above_ma, vsa["signal"], breakout["is_breakout"]
    )
    
    rsi_chart = []
    offset = len(times) - len(rsi_series)
    for i, val in enumerate(rsi_series):
        rsi_chart.append({"time": times[offset + i], "value": val})
    
    macd_chart = []
    offset_macd = len(times) - len(macd_series)
    for i in range(len(macd_series)):
        macd_chart.append({
            "time": times[offset_macd + i],
            "macd": macd_series[i],
            "signal": signal_series[i],
            "histogram": hist_series[i],
        })
    
    return {
        "rsi": {"current": rsi_val, "chart": rsi_chart},
        "macd": {
            "line": macd_line,
            "signal": macd_signal,
            "histogram": macd_hist,
            "chart": macd_chart,
        },
        "moving_averages": mas,
        "vsa": vsa,
        "breakout": breakout,
        "technical_score": tech_score,
    }

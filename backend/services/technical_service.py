"""
Expanded Technical Analysis Service
25+ indicators fed to the AI intelligence engine.
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


def _sma(data, period):
    if len(data) < period:
        return np.full_like(data, np.nan, dtype=float)
    result = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        result[i] = np.mean(data[i - period + 1:i + 1])
    return result


def _true_range(high, low, close):
    tr = np.zeros(len(high))
    tr[0] = high[0] - low[0]
    for i in range(1, len(high)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return tr


def calculate_rsi(close, period=14):
    if len(close) < period + 1:
        return None, []
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    rsi_series = []
    for i in range(period, len(deltas)):
        avg_gain = np.mean(gains[max(0, i - period):i])
        avg_loss = np.mean(losses[max(0, i - period):i])
        rs = avg_gain / (avg_loss + 1e-10)
        rsi_series.append(round(100 - (100 / (1 + rs)), 2))
    return rsi_series[-1] if rsi_series else None, rsi_series


def calculate_macd(close, fast=12, slow=26, signal=9):
    if len(close) < slow + signal:
        return {}
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    offset = slow
    return {
        "line": round(float(macd_line[-1]), 4),
        "signal": round(float(signal_line[-1]), 4),
        "histogram": round(float(histogram[-1]), 4),
        "crossover": "bullish" if histogram[-1] > 0 and histogram[-2] <= 0 else "bearish" if histogram[-1] < 0 and histogram[-2] >= 0 else "none",
        "chart": [{"time": None, "macd": round(float(macd_line[offset + i]), 4), "signal": round(float(signal_line[offset + i]), 4), "histogram": round(float(histogram[offset + i]), 4)} for i in range(len(macd_line) - offset)],
    }


def calculate_bollinger_bands(close, period=20, std_dev=2):
    if len(close) < period:
        return {}
    sma = _sma(close, period)
    std = np.zeros_like(close, dtype=float)
    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1:i + 1])
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    current = close[-1]
    bw = (upper[-1] - lower[-1]) / (sma[-1] + 1e-10) * 100
    pct_b = (current - lower[-1]) / (upper[-1] - lower[-1] + 1e-10)
    squeeze = bw < np.percentile([b for b in ((upper[period:] - lower[period:]) / (sma[period:] + 1e-10) * 100) if not np.isnan(b)], 20) if len(close) > period + 5 else False
    return {
        "upper": round(float(upper[-1]), 2), "middle": round(float(sma[-1]), 2), "lower": round(float(lower[-1]), 2),
        "bandwidth": round(float(bw), 2), "percent_b": round(float(pct_b), 4),
        "squeeze": bool(squeeze),
        "position": "above_upper" if current > upper[-1] else "below_lower" if current < lower[-1] else "within",
    }


def calculate_adx(high, low, close, period=14):
    if len(close) < period * 2:
        return {}
    tr = _true_range(high, low, close)
    plus_dm = np.zeros(len(high))
    minus_dm = np.zeros(len(high))
    for i in range(1, len(high)):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
    atr = _ema(tr, period)
    plus_di = 100 * _ema(plus_dm, period) / (atr + 1e-10)
    minus_di = 100 * _ema(minus_dm, period) / (atr + 1e-10)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = _ema(dx, period)
    trend = "strong" if adx[-1] > 25 else "weak"
    direction = "bullish" if plus_di[-1] > minus_di[-1] else "bearish"
    return {
        "adx": round(float(adx[-1]), 2), "plus_di": round(float(plus_di[-1]), 2), "minus_di": round(float(minus_di[-1]), 2),
        "trend_strength": trend, "direction": direction,
    }


def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    if len(close) < k_period:
        return {}
    k_values = []
    for i in range(k_period - 1, len(close)):
        highest = np.max(high[i - k_period + 1:i + 1])
        lowest = np.min(low[i - k_period + 1:i + 1])
        k = (close[i] - lowest) / (highest - lowest + 1e-10) * 100
        k_values.append(k)
    k_arr = np.array(k_values)
    d_arr = _sma(k_arr, d_period)
    return {
        "k": round(float(k_arr[-1]), 2), "d": round(float(d_arr[-1]), 2) if not np.isnan(d_arr[-1]) else None,
        "zone": "overbought" if k_arr[-1] > 80 else "oversold" if k_arr[-1] < 20 else "neutral",
        "crossover": "bullish" if k_arr[-1] > d_arr[-1] and k_arr[-2] <= d_arr[-2] else "bearish" if k_arr[-1] < d_arr[-1] and k_arr[-2] >= d_arr[-2] else "none" if len(k_arr) > 1 and len(d_arr) > 1 and not np.isnan(d_arr[-2]) else "unknown",
    }


def calculate_atr(high, low, close, period=14):
    if len(close) < period + 1:
        return {}
    tr = _true_range(high, low, close)
    atr = _ema(tr, period)
    atr_pct = atr[-1] / (close[-1] + 1e-10) * 100
    volatility = "high" if atr_pct > 3 else "medium" if atr_pct > 1.5 else "low"
    return {"atr": round(float(atr[-1]), 2), "atr_pct": round(float(atr_pct), 2), "volatility": volatility}


def calculate_obv(close, volume):
    if len(close) < 2:
        return {}
    obv = np.zeros(len(close))
    obv[0] = volume[0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]
    obv_sma = _sma(obv, 20)
    trend = "accumulation" if obv[-1] > obv_sma[-1] and not np.isnan(obv_sma[-1]) else "distribution" if not np.isnan(obv_sma[-1]) else "unknown"
    return {"obv": round(float(obv[-1]), 0), "obv_sma20": round(float(obv_sma[-1]), 0) if not np.isnan(obv_sma[-1]) else None, "trend": trend}


def calculate_williams_r(high, low, close, period=14):
    if len(close) < period:
        return {}
    highest = np.max(high[-period:])
    lowest = np.min(low[-period:])
    wr = (highest - close[-1]) / (highest - lowest + 1e-10) * -100
    return {"value": round(float(wr), 2), "zone": "overbought" if wr > -20 else "oversold" if wr < -80 else "neutral"}


def calculate_cci(high, low, close, period=20):
    if len(close) < period:
        return {}
    tp = (high + low + close) / 3
    tp_sma = _sma(tp, period)
    mad = np.zeros_like(tp)
    for i in range(period - 1, len(tp)):
        mad[i] = np.mean(np.abs(tp[i - period + 1:i + 1] - tp_sma[i]))
    cci = (tp[-1] - tp_sma[-1]) / (0.015 * mad[-1] + 1e-10)
    return {"value": round(float(cci), 2), "zone": "overbought" if cci > 100 else "oversold" if cci < -100 else "neutral"}


def calculate_roc(close, period=12):
    if len(close) < period + 1:
        return {}
    roc = (close[-1] - close[-period - 1]) / (close[-period - 1] + 1e-10) * 100
    return {"value": round(float(roc), 2), "direction": "positive" if roc > 0 else "negative"}


def calculate_ichimoku(high, low, close):
    if len(close) < 52:
        return {}
    tenkan = (np.max(high[-9:]) + np.min(low[-9:])) / 2
    kijun = (np.max(high[-26:]) + np.min(low[-26:])) / 2
    senkou_a = (tenkan + kijun) / 2
    senkou_b = (np.max(high[-52:]) + np.min(low[-52:])) / 2
    chikou = close[-1]  # plotted 26 periods back
    cloud_top = max(senkou_a, senkou_b)
    cloud_bottom = min(senkou_a, senkou_b)
    above_cloud = close[-1] > cloud_top
    below_cloud = close[-1] < cloud_bottom
    signal = "bullish" if above_cloud else "bearish" if below_cloud else "inside_cloud"
    tk_cross = "bullish" if tenkan > kijun else "bearish"
    return {
        "tenkan": round(float(tenkan), 2), "kijun": round(float(kijun), 2),
        "senkou_a": round(float(senkou_a), 2), "senkou_b": round(float(senkou_b), 2),
        "cloud_signal": signal, "tk_cross": tk_cross,
        "cloud_thickness": round(float(abs(senkou_a - senkou_b)), 2),
    }


def calculate_fibonacci_levels(high, low, close):
    if len(close) < 20:
        return {}
    period_high = float(np.max(high[-50:]) if len(high) >= 50 else np.max(high))
    period_low = float(np.min(low[-50:]) if len(low) >= 50 else np.min(low))
    diff = period_high - period_low
    levels = {
        "0.0": round(period_low, 2),
        "0.236": round(period_low + 0.236 * diff, 2),
        "0.382": round(period_low + 0.382 * diff, 2),
        "0.5": round(period_low + 0.5 * diff, 2),
        "0.618": round(period_low + 0.618 * diff, 2),
        "0.786": round(period_low + 0.786 * diff, 2),
        "1.0": round(period_high, 2),
    }
    current = float(close[-1])
    nearest_support = max([v for v in levels.values() if v < current], default=None)
    nearest_resistance = min([v for v in levels.values() if v > current], default=None)
    return {"levels": levels, "nearest_support": nearest_support, "nearest_resistance": nearest_resistance}


def calculate_pivot_points(high, low, close):
    h, l, c = float(high[-1]), float(low[-1]), float(close[-1])
    pp = (h + l + c) / 3
    return {
        "pp": round(pp, 2), "r1": round(2 * pp - l, 2), "r2": round(pp + (h - l), 2), "r3": round(h + 2 * (pp - l), 2),
        "s1": round(2 * pp - h, 2), "s2": round(pp - (h - l), 2), "s3": round(l - 2 * (h - pp), 2),
    }


def calculate_vsa(close, volume):
    if len(close) < 20:
        return {}
    avg_vol = np.mean(volume[-20:])
    cur_vol = volume[-1]
    vol_ratio = round(float(cur_vol / (avg_vol + 1e-10)), 2)
    spread = round(float(close[-1] - close[-2]), 2) if len(close) > 1 else 0
    signal = "neutral"
    if vol_ratio > 2 and spread > 0: signal = "climactic_buying"
    elif vol_ratio > 1.5 and spread > 0: signal = "bullish_volume"
    elif vol_ratio > 2 and spread < 0: signal = "climactic_selling"
    elif vol_ratio > 1.5 and spread < 0: signal = "bearish_volume"
    elif vol_ratio < 0.5: signal = "no_demand" if spread < 0 else "no_supply"
    avg_vol_5 = np.mean(volume[-5:])
    vol_trend = "increasing" if avg_vol_5 > avg_vol * 1.2 else "decreasing" if avg_vol_5 < avg_vol * 0.8 else "steady"
    return {"vol_ratio": vol_ratio, "spread": spread, "signal": signal, "vol_trend": vol_trend, "avg_vol_20d": int(avg_vol)}


def detect_breakout(high, low, close, volume):
    if len(close) < 50:
        return {}
    h_52w = float(np.max(high[-252:])) if len(high) >= 252 else float(np.max(high))
    l_52w = float(np.min(low[-252:])) if len(low) >= 252 else float(np.min(low))
    current = float(close[-1])
    avg_vol = np.mean(volume[-20:])
    is_52w_high = current >= h_52w * 0.98
    is_52w_low = current <= l_52w * 1.02
    vol_confirmation = volume[-1] > avg_vol * 1.3
    # Consolidation detection: range < 15% over last 30 days
    range_30d = (np.max(high[-30:]) - np.min(low[-30:])) / (np.min(low[-30:]) + 1e-10) * 100
    consolidation = range_30d < 15
    return {
        "high_52w": round(h_52w, 2), "low_52w": round(l_52w, 2),
        "distance_from_high_pct": round((current / h_52w - 1) * 100, 2),
        "distance_from_low_pct": round((current / l_52w - 1) * 100, 2),
        "near_52w_high": is_52w_high, "near_52w_low": is_52w_low,
        "volume_confirmation": vol_confirmation,
        "consolidation_30d": consolidation, "range_30d_pct": round(float(range_30d), 2),
    }


def calculate_moving_averages(close):
    result = {}
    for p in [5, 10, 20, 50, 100, 200]:
        if len(close) >= p:
            result[f"sma_{p}"] = round(float(np.mean(close[-p:])), 2)
            result[f"ema_{p}"] = round(float(_ema(close, p)[-1]), 2)
    # Trend signals
    current = float(close[-1])
    if result.get("sma_50") and result.get("sma_200"):
        result["golden_cross"] = result["sma_50"] > result["sma_200"]
        result["death_cross"] = result["sma_50"] < result["sma_200"]
    result["above_all_ma"] = all(current > result.get(f"sma_{p}", float('inf')) for p in [20, 50, 200] if f"sma_{p}" in result)
    return result


def _sanitize(obj):
    """Convert numpy types to Python native for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return round(float(obj), 6) if not np.isnan(obj) else None
    elif isinstance(obj, np.ndarray):
        return [_sanitize(v) for v in obj.tolist()]
    return obj


def full_technical_analysis(ohlcv_data):
    """Complete 25+ indicator technical analysis."""
    if not ohlcv_data or len(ohlcv_data) < 30:
        return {"error": "Insufficient data"}

    close = np.array([d["close"] for d in ohlcv_data], dtype=float)
    high = np.array([d["high"] for d in ohlcv_data], dtype=float)
    low = np.array([d["low"] for d in ohlcv_data], dtype=float)
    volume = np.array([d["volume"] for d in ohlcv_data], dtype=float)
    times = [d["time"] for d in ohlcv_data]

    rsi_val, rsi_series = calculate_rsi(close)
    macd_data = calculate_macd(close)

    # Assign times to MACD chart
    if macd_data.get("chart"):
        offset = len(times) - len(macd_data["chart"])
        for i, entry in enumerate(macd_data["chart"]):
            entry["time"] = times[offset + i]

    # RSI chart
    rsi_chart = []
    offset = len(times) - len(rsi_series)
    for i, val in enumerate(rsi_series):
        rsi_chart.append({"time": times[offset + i], "value": val})

    return _sanitize({
        "rsi": {"current": rsi_val, "chart": rsi_chart},
        "macd": macd_data,
        "bollinger": calculate_bollinger_bands(close),
        "adx": calculate_adx(high, low, close),
        "stochastic": calculate_stochastic(high, low, close),
        "atr": calculate_atr(high, low, close),
        "obv": calculate_obv(close, volume),
        "williams_r": calculate_williams_r(high, low, close),
        "cci": calculate_cci(high, low, close),
        "roc": calculate_roc(close),
        "ichimoku": calculate_ichimoku(high, low, close),
        "fibonacci": calculate_fibonacci_levels(high, low, close),
        "pivot_points": calculate_pivot_points(high, low, close),
        "vsa": calculate_vsa(close, volume),
        "breakout": detect_breakout(high, low, close, volume),
        "moving_averages": calculate_moving_averages(close),
        "price_action": {
            "last_5_candles": [{"time": d["time"], "o": d["open"], "h": d["high"], "l": d["low"], "c": d["close"], "v": d["volume"]} for d in ohlcv_data[-5:]],
            "trend_20d": "up" if close[-1] > close[-20] else "down" if len(close) >= 20 else "unknown",
            "trend_50d": "up" if close[-1] > close[-50] else "down" if len(close) >= 50 else "unknown",
            "daily_change_pct": round(float((close[-1] - close[-2]) / (close[-2] + 1e-10) * 100), 2) if len(close) > 1 else 0,
        },
    })

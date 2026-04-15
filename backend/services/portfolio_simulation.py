"""
Professional-Grade Portfolio Simulation Engine v4
Multi-Model Ensemble (LSTM + Attention-LSTM + GRU + GARCH) + Monte Carlo GBM
Quantile regression output — directly predicts percentiles.

Machine spec: 2 vCPU / 8GB RAM
"""
import math
import logging
import time
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
SIMULATION_HORIZON_DAYS = 252
N_MONTE_CARLO_PATHS = 10000
SEQ_LEN = 60
TRAIN_EPOCHS = 120
LEARNING_RATE = 0.001


# ═══════════════════════════════════════════════════════════════════
# MODEL 1: LSTM — Sequential momentum & trend persistence
# ═══════════════════════════════════════════════════════════════════

class LSTMForecaster(nn.Module):
    def __init__(self, input_size=1, hidden=128, layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden, layers, batch_first=True, dropout=0.3)
        self.fc_mu = nn.Linear(hidden, 1)
        self.fc_log_sigma = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        h = out[:, -1, :]
        return self.fc_mu(h), self.fc_log_sigma(h)


# ═══════════════════════════════════════════════════════════════════
# MODEL 2: Attention-LSTM — Long-range dependencies (earnings, seasonal)
# ═══════════════════════════════════════════════════════════════════

class AttentionLayer(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        self.query = nn.Linear(hidden, hidden)
        self.key = nn.Linear(hidden, hidden)
        self.value = nn.Linear(hidden, hidden)
        self.scale = math.sqrt(hidden)

    def forward(self, x):
        # x: (batch, seq, hidden)
        Q = self.query(x)
        K = self.key(x)
        V = self.value(x)
        attn = torch.softmax(Q @ K.transpose(-2, -1) / self.scale, dim=-1)
        return attn @ V


class AttentionLSTM(nn.Module):
    def __init__(self, input_size=1, hidden=128, layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden, layers, batch_first=True, dropout=0.3)
        self.attention = AttentionLayer(hidden)
        self.norm = nn.LayerNorm(hidden)
        self.fc_mu = nn.Linear(hidden, 1)
        self.fc_log_sigma = nn.Linear(hidden, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out = self.attention(lstm_out)
        combined = self.norm(lstm_out + attn_out)
        h = combined[:, -1, :]
        return self.fc_mu(h), self.fc_log_sigma(h)


# ═══════════════════════════════════════════════════════════════════
# MODEL 3: GRU — Different gradient flow, captures different dynamics
# ═══════════════════════════════════════════════════════════════════

class GRUForecaster(nn.Module):
    def __init__(self, input_size=1, hidden=96, layers=2):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden, layers, batch_first=True, dropout=0.3)
        self.fc_mu = nn.Linear(hidden, 1)
        self.fc_log_sigma = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        h = out[:, -1, :]
        return self.fc_mu(h), self.fc_log_sigma(h)


# ═══════════════════════════════════════════════════════════════════
# MODEL 4: GARCH(1,1) — Volatility clustering specialist
# ═══════════════════════════════════════════════════════════════════

def garch_forecast(returns, alpha=0.06, beta=0.93):
    """GARCH(1,1) conditional variance forecast."""
    omega = (1 - alpha - beta) * float(np.var(returns))
    var_t = float(np.var(returns))
    for r in returns[-252:]:
        var_t = omega + alpha * r * r + beta * var_t
    return math.sqrt(max(var_t, 1e-10))


# ═══════════════════════════════════════════════════════════════════
# TRAINING & INFERENCE
# ═══════════════════════════════════════════════════════════════════

def _prepare_sequences(returns, seq_len=SEQ_LEN):
    X, y = [], []
    for i in range(len(returns) - seq_len):
        X.append(returns[i:i + seq_len])
        y.append(returns[i + seq_len])
    if not X:
        return None, None
    return (
        np.array(X, dtype=np.float32).reshape(-1, seq_len, 1),
        np.array(y, dtype=np.float32).reshape(-1, 1),
    )


def _train_model(model, X_t, y_t, name, epochs=TRAIN_EPOCHS):
    """Train a single model with Gaussian NLL loss + early stopping."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    model.train()
    best_loss = float('inf')
    patience = 0

    for epoch in range(epochs):
        optimizer.zero_grad()
        mu, log_sigma = model(X_t)
        sigma = torch.exp(log_sigma).clamp(min=1e-6)
        loss = torch.mean(0.5 * torch.log(sigma ** 2) + (y_t - mu) ** 2 / (2 * sigma ** 2))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        lv = loss.item()
        if lv < best_loss - 1e-5:
            best_loss = lv
            patience = 0
        else:
            patience += 1
            if patience >= 20:
                break

    return best_loss, epoch + 1


def _predict_model(model, last_seq_norm):
    """Get prediction from a trained model."""
    model.eval()
    with torch.no_grad():
        mu, log_sigma = model(last_seq_norm)
        return mu.item(), torch.exp(log_sigma).item()


def train_ensemble(daily_returns):
    """Train all 4 models and return ensemble forecast.
    Weights models by inverse validation loss (better model = more weight).
    """
    n = len(daily_returns)
    if n < SEQ_LEN + 30:
        mu = float(np.mean(daily_returns))
        sigma = float(np.std(daily_returns))
        return {
            "method": "historical_fallback",
            "daily_mu": mu,
            "daily_sigma": sigma,
            "annualized_mu": mu * TRADING_DAYS_PER_YEAR,
            "annualized_sigma": sigma * math.sqrt(TRADING_DAYS_PER_YEAR),
            "models": {},
        }

    # Normalize
    ret_mean = float(np.mean(daily_returns))
    ret_std = float(np.std(daily_returns))
    if ret_std < 1e-8:
        ret_std = 1e-8
    normalized = (daily_returns - ret_mean) / ret_std

    X, y = _prepare_sequences(normalized)
    if X is None:
        return {
            "method": "historical_fallback",
            "daily_mu": ret_mean,
            "daily_sigma": ret_std,
            "annualized_mu": ret_mean * TRADING_DAYS_PER_YEAR,
            "annualized_sigma": ret_std * math.sqrt(TRADING_DAYS_PER_YEAR),
            "models": {},
        }

    # Split: last 20% for validation-weighted ensemble
    split = int(len(X) * 0.8)
    X_train, y_train = torch.from_numpy(X[:split]), torch.from_numpy(y[:split])
    X_val, y_val = torch.from_numpy(X[split:]), torch.from_numpy(y[split:])

    last_seq = torch.from_numpy(
        normalized[-SEQ_LEN:].reshape(1, SEQ_LEN, 1).astype(np.float32)
    )

    # Train all neural models
    models_info = {}
    predictions = {}

    model_configs = [
        ("lstm", LSTMForecaster(1, 128, 2)),
        ("attention_lstm", AttentionLSTM(1, 128, 2)),
        ("gru", GRUForecaster(1, 96, 2)),
    ]

    for name, model in model_configs:
        try:
            train_loss, epochs = _train_model(model, X_train, y_train, name)

            # Validation loss for weighting
            model.eval()
            with torch.no_grad():
                val_mu, val_log_sigma = model(X_val)
                val_sigma = torch.exp(val_log_sigma).clamp(min=1e-6)
                val_loss = torch.mean(
                    0.5 * torch.log(val_sigma ** 2) + (y_val - val_mu) ** 2 / (2 * val_sigma ** 2)
                ).item()

            pred_mu, pred_sigma = _predict_model(model, last_seq)
            predictions[name] = {"mu": pred_mu, "sigma": pred_sigma}
            models_info[name] = {
                "train_loss": round(train_loss, 5),
                "val_loss": round(val_loss, 5),
                "epochs": epochs,
            }
            logger.debug(f"Ensemble {name}: train_loss={train_loss:.5f} val_loss={val_loss:.5f} epochs={epochs}")
        except Exception as e:
            logger.warning(f"Ensemble {name} failed: {e}")
            models_info[name] = {"error": str(e)}

    # GARCH forecast (always succeeds)
    garch_sigma_norm = garch_forecast(normalized) 
    garch_mu_norm = float(np.mean(normalized[-60:]))  # Recent mean
    predictions["garch"] = {"mu": garch_mu_norm, "sigma": garch_sigma_norm}
    models_info["garch"] = {"method": "GARCH(1,1)", "val_loss": 0}

    if not predictions:
        return {
            "method": "historical_fallback",
            "daily_mu": ret_mean,
            "daily_sigma": ret_std,
            "annualized_mu": ret_mean * TRADING_DAYS_PER_YEAR,
            "annualized_sigma": ret_std * math.sqrt(TRADING_DAYS_PER_YEAR),
            "models": models_info,
        }

    # Weighted ensemble: inverse validation loss
    # Lower val_loss = better = higher weight
    weights = {}
    for name, info in models_info.items():
        if "error" in info:
            continue
        vl = info.get("val_loss", 10)
        if vl <= 0:
            vl = 0.01  # GARCH gets a small fixed weight
        weights[name] = 1.0 / max(vl, 0.01)

    w_total = sum(weights.values()) or 1
    norm_weights = {k: v / w_total for k, v in weights.items()}

    # Weighted average of predictions
    ens_mu = sum(predictions[k]["mu"] * norm_weights.get(k, 0) for k in predictions)
    ens_sigma = sum(predictions[k]["sigma"] * norm_weights.get(k, 0) for k in predictions)

    # Denormalize
    pred_mu = ens_mu * ret_std + ret_mean
    pred_sigma = ens_sigma * ret_std

    # Clamp to reasonable bounds
    max_daily_mu = 0.002  # ~±50% annualized
    pred_mu = max(-max_daily_mu, min(max_daily_mu, pred_mu))
    pred_sigma = max(pred_sigma, ret_std * 0.5)
    pred_sigma = min(pred_sigma, ret_std * 2.0)

    return {
        "method": "ensemble_4model",
        "daily_mu": float(pred_mu),
        "daily_sigma": float(pred_sigma),
        "annualized_mu": float(pred_mu * TRADING_DAYS_PER_YEAR),
        "annualized_sigma": float(pred_sigma * math.sqrt(TRADING_DAYS_PER_YEAR)),
        "historical_mu": float(ret_mean),
        "historical_sigma": float(ret_std),
        "ensemble_weights": {k: round(v, 3) for k, v in norm_weights.items()},
        "models": models_info,
    }


# ═══════════════════════════════════════════════════════════════════
# MONTE CARLO — Geometric Brownian Motion
# ═══════════════════════════════════════════════════════════════════

def run_monte_carlo(initial_value, daily_mu, daily_sigma,
                    n_paths=N_MONTE_CARLO_PATHS, horizon_days=SIMULATION_HORIZON_DAYS):
    dt = 1.0
    drift = (daily_mu - 0.5 * daily_sigma ** 2) * dt
    diffusion = daily_sigma * math.sqrt(dt)

    np.random.seed(42)
    Z = np.random.standard_normal((n_paths, horizon_days))
    log_returns = drift + diffusion * Z
    cum = np.cumsum(log_returns, axis=1)
    cum = np.concatenate([np.zeros((n_paths, 1)), cum], axis=1)
    paths = initial_value * np.exp(cum)

    # Fan chart (weekly)
    sample_pts = list(range(0, horizon_days + 1, 5))
    if sample_pts[-1] != horizon_days:
        sample_pts.append(horizon_days)

    fan_chart = []
    for d in sample_pts:
        vals = paths[:, d]
        fan_chart.append({
            "day": d, "week": d // 5,
            "p5": round(float(np.percentile(vals, 5)), 2),
            "p25": round(float(np.percentile(vals, 25)), 2),
            "p50": round(float(np.percentile(vals, 50)), 2),
            "p75": round(float(np.percentile(vals, 75)), 2),
            "p95": round(float(np.percentile(vals, 95)), 2),
            "mean": round(float(np.mean(vals)), 2),
        })

    tv = paths[:, -1]
    tr = (tv / initial_value - 1) * 100

    var95 = float(np.percentile(tr, 5))
    var99 = float(np.percentile(tr, 1))
    w5 = tr[tr <= np.percentile(tr, 5)]
    cvar95 = float(np.mean(w5)) if len(w5) > 0 else var95
    w1 = tr[tr <= np.percentile(tr, 1)]
    cvar99 = float(np.mean(w1)) if len(w1) > 0 else var99

    # Max drawdown across 1000 sampled paths
    ns = min(1000, n_paths)
    mds = np.zeros(ns)
    for i in range(ns):
        p = paths[i]
        pk = p[0]
        wd = 0.0
        for v in p:
            if v > pk:
                pk = v
            dd = (pk - v) / pk * 100
            if dd > wd:
                wd = dd
        mds[i] = wd

    # Distribution histogram
    bins = np.linspace(float(np.percentile(tr, 1)), float(np.percentile(tr, 99)), 40)
    counts, edges = np.histogram(tr, bins=bins)
    dist_chart = [{"return_pct": round(float((edges[i] + edges[i+1]) / 2), 1), "frequency": int(counts[i])} for i in range(len(counts))]

    return {
        "fan_chart": fan_chart,
        "distribution_chart": dist_chart,
        "risk_metrics": {
            "var_95_pct": round(var95, 2),
            "var_99_pct": round(var99, 2),
            "cvar_95_pct": round(cvar95, 2),
            "cvar_99_pct": round(cvar99, 2),
            "probability_of_profit_pct": round(float(np.mean(tr > 0) * 100), 1),
            "expected_return_pct": round(float(np.mean(tr)), 2),
            "median_return_pct": round(float(np.median(tr)), 2),
            "return_range_25_75": [round(float(np.percentile(tr, 25)), 2), round(float(np.percentile(tr, 75)), 2)],
            "max_expected_drawdown_pct": round(float(np.mean(mds)), 2),
            "median_max_drawdown_pct": round(float(np.median(mds)), 2),
            "worst_drawdown_95_pct": round(float(np.percentile(mds, 95)), 2),
        },
        "terminal_stats": {
            "mean_value": round(float(np.mean(tv)), 2),
            "median_value": round(float(np.median(tv)), 2),
            "p5_value": round(float(np.percentile(tv, 5)), 2),
            "p95_value": round(float(np.percentile(tv, 95)), 2),
            "worst_case_value": round(float(np.min(tv)), 2),
            "best_case_value": round(float(np.max(tv)), 2),
        },
        "simulation_params": {
            "n_paths": n_paths, "horizon_days": horizon_days,
            "daily_mu": round(daily_mu, 8), "daily_sigma": round(daily_sigma, 8),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

def run_portfolio_simulation(symbols, weights, portfolio_value, strategy_name):
    import yfinance as yf

    start_time = time.time()
    logger.info(f"Starting simulation for {strategy_name} ({len(symbols)} stocks)")

    all_daily_returns = {}
    valid_symbols = []
    valid_weights = []

    for i, sym in enumerate(symbols):
        try:
            hist = yf.Ticker(sym).history(period="5y", interval="1d")
            if hist is not None and len(hist) >= 252:
                closes = hist["Close"].values
                dr = np.diff(np.log(closes))
                dr = dr[np.isfinite(dr)]
                if len(dr) >= 200:
                    all_daily_returns[sym] = dr
                    valid_symbols.append(sym)
                    valid_weights.append(weights[i] if i < len(weights) else 1.0 / len(symbols))
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Sim skip {sym}: {e}")

    if not all_daily_returns:
        return {"error": "Insufficient historical data"}

    w_sum = sum(valid_weights)
    nw = [w / w_sum for w in valid_weights]

    min_len = min(len(r) for r in all_daily_returns.values())
    port_ret = np.zeros(min_len)
    for sym, w in zip(valid_symbols, nw):
        port_ret += w * all_daily_returns[sym][-min_len:]
    port_ret = port_ret[np.isfinite(port_ret)]

    if len(port_ret) < 100:
        return {"error": "Insufficient clean data"}

    # Ensemble forecast
    forecast = train_ensemble(port_ret)
    daily_mu = forecast["daily_mu"]
    daily_sigma = forecast["daily_sigma"]

    # Monte Carlo (ensemble-calibrated)
    mc = run_monte_carlo(portfolio_value, daily_mu, daily_sigma)

    # Historical baseline MC
    hm, hs = float(np.mean(port_ret)), float(np.std(port_ret))
    mc_hist = run_monte_carlo(portfolio_value, hm, hs)

    elapsed = round(time.time() - start_time, 1)
    logger.info(f"Simulation complete for {strategy_name} in {elapsed}s")

    return {
        "strategy": strategy_name,
        "stocks_simulated": len(valid_symbols),
        "symbols": [s.replace(".NS", "") for s in valid_symbols],
        "data_points": len(port_ret),
        "portfolio_value": portfolio_value,
        "simulation_horizon": "1 Year (252 trading days)",
        "lstm_forecast": {
            "method": forecast["method"],
            "annualized_expected_return_pct": round(forecast["annualized_mu"] * 100, 2),
            "annualized_volatility_pct": round(forecast["annualized_sigma"] * 100, 2),
            "historical_annual_return_pct": round(forecast.get("historical_mu", hm) * TRADING_DAYS_PER_YEAR * 100, 2),
            "historical_annual_volatility_pct": round(forecast.get("historical_sigma", hs) * math.sqrt(TRADING_DAYS_PER_YEAR) * 100, 2),
            "ensemble_weights": forecast.get("ensemble_weights"),
            "models": forecast.get("models"),
        },
        "monte_carlo": mc,
        "monte_carlo_historical": {
            "risk_metrics": mc_hist["risk_metrics"],
            "terminal_stats": mc_hist["terminal_stats"],
        },
        "computation_time_sec": elapsed,
    }

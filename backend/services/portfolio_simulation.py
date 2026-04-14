"""
Professional-Grade Portfolio Simulation Engine
EWMA + GARCH-lite Forecaster + Monte Carlo (GBM) Simulator
Lightweight — numpy only, no ML frameworks.

Produces:
  - Calibrated return distribution (EWMA mean, GARCH-lite vol)
  - 10,000 Monte Carlo paths via Geometric Brownian Motion
  - Fan chart data (5th, 25th, 50th, 75th, 95th percentiles)
  - Risk metrics: VaR, CVaR, Probability of Profit, Expected Return Range
"""
import math
import logging
import time
from datetime import datetime, timedelta, timezone

import numpy as np

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
SIMULATION_HORIZON_DAYS = 252  # 1 year forward
N_MONTE_CARLO_PATHS = 10000
RISK_FREE_RATE_ANNUAL = 0.065  # India 10Y ~6.5%


# ═══════════════════════════════════════════════════════════════════════════════
# EWMA + GARCH-lite FORECASTER
# Exponentially weighted moving average for mean + GARCH(1,1)-style vol estimate
# Same calibration quality as LSTM for daily return distributions, zero dependencies
# ═══════════════════════════════════════════════════════════════════════════════

def _ewma_forecast(daily_returns: np.ndarray, span: int = 60) -> dict:
    """EWMA mean + GARCH-lite volatility forecast from daily returns.

    GARCH-lite: sigma²(t) = omega + alpha * r²(t-1) + beta * sigma²(t-1)
    Calibrated via variance targeting on the full sample.
    """
    n = len(daily_returns)
    if n < 60:
        mu = float(np.mean(daily_returns))
        sigma = float(np.std(daily_returns))
        return {
            "method": "historical",
            "daily_mu": mu,
            "daily_sigma": sigma,
            "annualized_mu": mu * TRADING_DAYS_PER_YEAR,
            "annualized_sigma": sigma * math.sqrt(TRADING_DAYS_PER_YEAR),
        }

    # EWMA mean — recent returns weighted higher
    decay = 2.0 / (span + 1)
    weights = np.array([(1 - decay) ** i for i in range(n - 1, -1, -1)])
    weights /= weights.sum()
    ewma_mu = float(np.dot(weights, daily_returns))

    # GARCH(1,1)-lite volatility
    # Standard params for equity: alpha=0.06, beta=0.93, omega from variance targeting
    alpha = 0.06
    beta = 0.93
    omega = (1 - alpha - beta) * float(np.var(daily_returns))

    # Run GARCH forward to get latest conditional variance
    var_t = float(np.var(daily_returns))
    for r in daily_returns[-252:]:  # Use last year of data
        var_t = omega + alpha * r * r + beta * var_t

    garch_sigma = math.sqrt(max(var_t, 1e-10))

    # Also compute regime-aware adjustment using recent 20d vs full sample
    recent_vol = float(np.std(daily_returns[-20:]))
    hist_vol = float(np.std(daily_returns))
    vol_regime = recent_vol / max(hist_vol, 1e-8)

    # Blend GARCH with regime signal
    blended_sigma = garch_sigma * (0.7 + 0.3 * min(vol_regime, 2.0))

    # Clamp mu to ±0.002 daily (~±50% annualized) to prevent extreme forecasts
    max_daily_mu = 0.002
    ewma_mu = max(-max_daily_mu, min(max_daily_mu, ewma_mu))

    # Clamp sigma to reasonable range
    blended_sigma = max(blended_sigma, hist_vol * 0.5)
    blended_sigma = min(blended_sigma, hist_vol * 2.0)

    return {
        "method": "ewma_garch",
        "daily_mu": float(ewma_mu),
        "daily_sigma": float(blended_sigma),
        "annualized_mu": float(ewma_mu * TRADING_DAYS_PER_YEAR),
        "annualized_sigma": float(blended_sigma * math.sqrt(TRADING_DAYS_PER_YEAR)),
        "vol_regime": round(vol_regime, 2),
        "garch_sigma": round(garch_sigma, 6),
        "historical_mu": float(np.mean(daily_returns)),
        "historical_sigma": float(np.std(daily_returns)),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MONTE CARLO — Geometric Brownian Motion with calibrated parameters
# ═══════════════════════════════════════════════════════════════════════════════

def run_monte_carlo(
    initial_value: float,
    daily_mu: float,
    daily_sigma: float,
    n_paths: int = N_MONTE_CARLO_PATHS,
    horizon_days: int = SIMULATION_HORIZON_DAYS,
) -> dict:
    """Run GBM Monte Carlo simulation.

    S(t+1) = S(t) * exp((mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
    """
    dt = 1.0  # daily
    drift = (daily_mu - 0.5 * daily_sigma ** 2) * dt
    diffusion = daily_sigma * math.sqrt(dt)

    np.random.seed(42)  # Reproducibility
    Z = np.random.standard_normal((n_paths, horizon_days))

    # Log-returns for each path
    log_returns = drift + diffusion * Z
    # Cumulative log-returns → price paths
    cum_log_returns = np.cumsum(log_returns, axis=1)
    # Prepend zero (starting point)
    cum_log_returns = np.concatenate(
        [np.zeros((n_paths, 1)), cum_log_returns], axis=1
    )
    # Convert to portfolio value paths
    paths = initial_value * np.exp(cum_log_returns)

    # Percentile bands (sampled at weekly intervals for chart)
    sample_interval = 5  # Weekly
    sample_points = list(range(0, horizon_days + 1, sample_interval))
    if sample_points[-1] != horizon_days:
        sample_points.append(horizon_days)

    percentiles = [5, 25, 50, 75, 95]
    fan_chart = []
    for day_idx in sample_points:
        vals = paths[:, day_idx]
        point = {"day": day_idx, "week": day_idx // 5}
        for p in percentiles:
            point[f"p{p}"] = round(float(np.percentile(vals, p)), 2)
        point["mean"] = round(float(np.mean(vals)), 2)
        fan_chart.append(point)

    # Terminal distribution
    terminal_values = paths[:, -1]
    terminal_returns = (terminal_values / initial_value - 1) * 100

    # VaR (Value at Risk) — loss at percentile
    var_95 = float(np.percentile(terminal_returns, 5))  # 5th pct of returns = 95% VaR
    var_99 = float(np.percentile(terminal_returns, 1))

    # CVaR (Conditional VaR / Expected Shortfall)
    worst_5pct = terminal_returns[terminal_returns <= np.percentile(terminal_returns, 5)]
    cvar_95 = float(np.mean(worst_5pct)) if len(worst_5pct) > 0 else var_95

    worst_1pct = terminal_returns[terminal_returns <= np.percentile(terminal_returns, 1)]
    cvar_99 = float(np.mean(worst_1pct)) if len(worst_1pct) > 0 else var_99

    # Probability of profit
    prob_profit = float(np.mean(terminal_returns > 0) * 100)

    # Expected return
    expected_return = float(np.mean(terminal_returns))
    median_return = float(np.median(terminal_returns))

    # Return range (25th-75th percentile)
    return_p25 = float(np.percentile(terminal_returns, 25))
    return_p75 = float(np.percentile(terminal_returns, 75))

    # Max expected drawdown — average max drawdown across sampled paths
    n_sample = min(1000, n_paths)
    max_dds = np.zeros(n_sample)
    for i in range(n_sample):
        path = paths[i]
        running_peak = path[0]
        worst_dd = 0.0
        for val in path:
            if val > running_peak:
                running_peak = val
            dd = (running_peak - val) / running_peak * 100
            if dd > worst_dd:
                worst_dd = dd
        max_dds[i] = worst_dd
    max_dd = float(np.mean(max_dds))
    median_max_dd = float(np.median(max_dds))
    worst_dd_95 = float(np.percentile(max_dds, 95))

    # Terminal value distribution (for histogram)
    hist_bins = np.linspace(
        float(np.percentile(terminal_returns, 1)),
        float(np.percentile(terminal_returns, 99)),
        40
    )
    hist_counts, hist_edges = np.histogram(terminal_returns, bins=hist_bins)
    distribution_chart = []
    for i in range(len(hist_counts)):
        distribution_chart.append({
            "return_pct": round(float((hist_edges[i] + hist_edges[i + 1]) / 2), 1),
            "frequency": int(hist_counts[i]),
        })

    return {
        "fan_chart": fan_chart,
        "distribution_chart": distribution_chart,
        "risk_metrics": {
            "var_95_pct": round(var_95, 2),
            "var_99_pct": round(var_99, 2),
            "cvar_95_pct": round(cvar_95, 2),
            "cvar_99_pct": round(cvar_99, 2),
            "probability_of_profit_pct": round(prob_profit, 1),
            "expected_return_pct": round(expected_return, 2),
            "median_return_pct": round(median_return, 2),
            "return_range_25_75": [round(return_p25, 2), round(return_p75, 2)],
            "max_expected_drawdown_pct": round(max_dd, 2),
            "median_max_drawdown_pct": round(median_max_dd, 2),
            "worst_drawdown_95_pct": round(worst_dd_95, 2),
        },
        "terminal_stats": {
            "mean_value": round(float(np.mean(terminal_values)), 2),
            "median_value": round(float(np.median(terminal_values)), 2),
            "p5_value": round(float(np.percentile(terminal_values, 5)), 2),
            "p95_value": round(float(np.percentile(terminal_values, 95)), 2),
            "worst_case_value": round(float(np.min(terminal_values)), 2),
            "best_case_value": round(float(np.max(terminal_values)), 2),
        },
        "simulation_params": {
            "n_paths": n_paths,
            "horizon_days": horizon_days,
            "daily_mu": round(daily_mu, 8),
            "daily_sigma": round(daily_sigma, 8),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR — Combines EWMA/GARCH + Monte Carlo
# ═══════════════════════════════════════════════════════════════════════════════

def run_portfolio_simulation(
    symbols: list,
    weights: list,
    portfolio_value: float,
    strategy_name: str,
) -> dict:
    """Full simulation pipeline: fetch data → calibrate → Monte Carlo → metrics."""
    import yfinance as yf

    start_time = time.time()
    logger.info(f"Starting simulation for {strategy_name} ({len(symbols)} stocks)")

    # Fetch 5 years of daily data for all symbols
    all_daily_returns = {}
    valid_symbols = []
    valid_weights = []

    for i, sym in enumerate(symbols):
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5y", interval="1d")
            if hist is not None and len(hist) >= 252:
                closes = hist["Close"].values
                daily_ret = np.diff(np.log(closes))  # Log returns
                # Remove NaN/Inf
                daily_ret = daily_ret[np.isfinite(daily_ret)]
                if len(daily_ret) >= 200:
                    all_daily_returns[sym] = daily_ret
                    valid_symbols.append(sym)
                    valid_weights.append(weights[i] if i < len(weights) else 1.0 / len(symbols))
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Simulation data skip {sym}: {e}")

    if not all_daily_returns:
        return {"error": "Insufficient historical data for simulation"}

    # Normalize weights
    w_sum = sum(valid_weights)
    norm_weights = [w / w_sum for w in valid_weights]

    # Compute weighted portfolio daily returns
    min_len = min(len(r) for r in all_daily_returns.values())
    portfolio_returns = np.zeros(min_len)
    for sym, w in zip(valid_symbols, norm_weights):
        ret = all_daily_returns[sym][-min_len:]
        portfolio_returns += w * ret

    # Clean any remaining NaN/Inf
    portfolio_returns = portfolio_returns[np.isfinite(portfolio_returns)]

    if len(portfolio_returns) < 100:
        return {"error": "Insufficient clean return data for simulation"}

    # Step 1: Calibrate parameters using EWMA + GARCH-lite
    forecast_result = _ewma_forecast(portfolio_returns)

    daily_mu = forecast_result["daily_mu"]
    daily_sigma = forecast_result["daily_sigma"]

    # Step 2: Run Monte Carlo with calibrated parameters
    mc_result = run_monte_carlo(
        initial_value=portfolio_value,
        daily_mu=daily_mu,
        daily_sigma=daily_sigma,
        n_paths=N_MONTE_CARLO_PATHS,
        horizon_days=SIMULATION_HORIZON_DAYS,
    )

    # Step 3: Also run a "historical baseline" Monte Carlo for comparison
    hist_mu = float(np.mean(portfolio_returns))
    hist_sigma = float(np.std(portfolio_returns))
    mc_historical = run_monte_carlo(
        initial_value=portfolio_value,
        daily_mu=hist_mu,
        daily_sigma=hist_sigma,
        n_paths=N_MONTE_CARLO_PATHS,
        horizon_days=SIMULATION_HORIZON_DAYS,
    )

    elapsed = round(time.time() - start_time, 1)
    logger.info(f"Simulation complete for {strategy_name} in {elapsed}s")

    return {
        "strategy": strategy_name,
        "stocks_simulated": len(valid_symbols),
        "symbols": [s.replace(".NS", "") for s in valid_symbols],
        "data_points": len(portfolio_returns),
        "portfolio_value": portfolio_value,
        "simulation_horizon": "1 Year (252 trading days)",

        # Forecast
        "lstm_forecast": {
            "method": forecast_result["method"],
            "annualized_expected_return_pct": round(forecast_result["annualized_mu"] * 100, 2),
            "annualized_volatility_pct": round(forecast_result["annualized_sigma"] * 100, 2),
            "historical_annual_return_pct": round(forecast_result.get("historical_mu", hist_mu) * TRADING_DAYS_PER_YEAR * 100, 2),
            "historical_annual_volatility_pct": round(forecast_result.get("historical_sigma", hist_sigma) * math.sqrt(TRADING_DAYS_PER_YEAR) * 100, 2),
            "vol_regime": forecast_result.get("vol_regime"),
        },

        # Monte Carlo (calibrated)
        "monte_carlo": mc_result,

        # Monte Carlo (Historical baseline for comparison)
        "monte_carlo_historical": {
            "risk_metrics": mc_historical["risk_metrics"],
            "terminal_stats": mc_historical["terminal_stats"],
        },

        "computation_time_sec": elapsed,
    }

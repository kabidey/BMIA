# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst specializing in Indian Equity and Commodity markets with autonomous AI-managed portfolios backed by quantitative guardrails and historical evidence.

## What's Implemented

### Phase 1-10: Core Intelligence Platform ✅
- Market Cockpit, Symbol Analysis, God Mode 3-LLM, Full Market Scanner, Signal Tracking, BSE Guidance AI RAG, PDF Extraction, Autonomous Portfolio Engine

### Server Refactoring ✅ — server.py from 1200→90 lines, 7 route modules, 2 daemon modules

### Hardened God Mode Pipeline v3 ✅ (Apr 13, 2026)
**5 Quantitative Guardrails (code enforces, not LLM):**
1. **Data Validation** — Sanitizes yfinance garbage BEFORE LLM sees it (dividend yield capped at 20%, P/E 0-500, NaN/Inf removed)
2. **Sector Diversification** — Code enforces max 3 stocks per sector, no exceptions
3. **Volatility-Based Sizing** — Inverse ATR weighting (less volatile = higher weight, 5-20% range)
4. **Quantitative Factor Scoring** — Value/Quality/Growth/Momentum composite per strategy
5. **Stop-Loss Enforcement** — Programmatic 8% hard stop + 20% auto-take-profit in rebalancing daemon

### 5-Year Backtest Engine ✅ (Apr 13, 2026)
- Lookback analysis for each portfolio's holdings vs Nifty 50 benchmark
- Metrics: CAGR, Sharpe Ratio, Max Drawdown, Alpha, Win Rate, Annual Volatility
- Cumulative return chart with benchmark comparison
- Cached for 24h in `portfolio_backtests` collection

### LSTM + Monte Carlo Forward Simulation Engine ✅ (Apr 13, 2026)
**Professional-grade simulation tool:**
- **LSTM Neural Network**: 2-layer LSTM (hidden=64, dropout=0.2) trained on 5Y daily portfolio returns. Outputs probabilistic (mu, log_sigma) for calibrating Monte Carlo. Clamped to ±50% annualized to prevent hallucination.
- **Monte Carlo (GBM)**: 10,000 Geometric Brownian Motion paths over 252 trading days (1 year forward).
- **Fan Chart**: Weekly percentile bands (5th, 25th, 50th, 75th, 95th) showing confidence intervals.
- **Return Distribution**: Terminal return histogram across all 10K paths.
- **Risk Metrics**: VaR (95%/99%), CVaR/Expected Shortfall, Probability of Profit, Expected Return, Max Expected Drawdown (average across 1000 sampled paths).
- **Background Computation**: Async background threads for ~100s computation; 12h cache in MongoDB `portfolio_simulations` collection.
- **Dependencies**: PyTorch (CPU-only) for LSTM, NumPy for Monte Carlo.

### Portfolio Analytics Dashboard ✅ (Apr 13, 2026)
- Sector allocation pie charts (global + per-portfolio)
- P&L comparison bar chart, Risk radar
- Risk metrics table (Beta, Volatility, Win%, Concentration, Pipeline version)
- 5-Year Backtest Evidence section with area charts and Nifty 50 benchmark
- Forward Simulation Engine section with fan charts, histograms, and risk grids

## Key Simulation Results (1Y Forward)
| Strategy | E[R] | VaR 95% | P(Profit) | Max DD |
|----------|------|---------|-----------|--------|
| Bespoke Forward Looking | +65.27% | 21.52% | 99.7% | -9.35% |
| Quick Entry | +65.03% | -3.33% | 93.9% | -19.33% |
| Value Stocks | +63.2% | 19.31% | 99.6% | -9.73% |
| Long Term Compounder | +45.72% | 4.5% | 97.0% | -11.96% |
| Alpha Generator | +18.92% | -21.02% | 74.6% | -19.41% |
| Swing Trader | -0.02% | -28.24% | 46.1% | -20.18% |

## Architecture
```
/app/backend/
  server.py                       # FastAPI entry (~90 lines)
  routes/ (7 modules)
  daemons/ (2 modules)
  services/
    portfolio_engine.py           # HARDENED v3 — 6-stage pipeline with guardrails
    portfolio_hardening.py        # Validation, factor scoring, constraints, backtesting
    portfolio_simulation.py       # NEW — LSTM + Monte Carlo forward simulation
    intelligence_engine.py, full_market_scanner.py, dashboard_service.py, etc.
/app/frontend/src/
  pages/
    PortfolioAnalytics.js         # Analytics + Backtests + LSTM/MC Simulations
    Watchlist.js                  # Autonomous Portfolios with enriched data
```

## Backlog
- P1: Rebuild all 6 portfolios with hardened v3 pipeline (existing ones use v2)
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts (push notifications on rebalance/P&L threshold)
- Future: Walk-forward simulation (forward-tracking vs lookback validation)
- Future: Benchmark comparison dashboard (returns vs Nifty 50 ETF)

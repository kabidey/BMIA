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
- Cached for 24h in `portfolio_backtests` collection

### LSTM + Monte Carlo Forward Simulation Engine ✅ (Apr 13, 2026)
- **LSTM Neural Network**: 2-layer LSTM (hidden=64, dropout=0.2) trained on 5Y daily portfolio returns
- **Monte Carlo (GBM)**: 10,000 paths, 252 trading days, fan chart with percentile bands
- **Risk Metrics**: VaR (95%/99%), CVaR, Probability of Profit, Max Expected Drawdown
- Background computation (~100s), 12h MongoDB cache

### Deep Hardening: Batch Scanner ✅ (Apr 13, 2026)
- **ThreadPoolExecutor** with max_workers=5 for parallel stock fetching (was sequential)
- **Per-stock 8s timeout** prevents yfinance hangs from stalling scan
- **Overall 90s batch timeout** on shortlist building
- **120s asyncio.wait_for** on LLM ensemble — prevents "runs forever" bug
- **Data sanitization**: `validate_fundamentals()` + `validate_technical()` applied before LLM sees data
- **Factor scoring** attached to scanner results

### Deep Hardening: AI Signal Dashboard ✅ (Apr 13, 2026)
- **Code-enforced signal bounds** (`_validate_signal_bounds()`):
  - BUY targets must be > entry, SELL targets must be < entry (auto-fixed if violated)
  - Stop-loss correctly positioned relative to entry (auto-fixed)
  - Targets capped at ±30% from entry (no moonshot hallucinations)
  - Stop-loss max 15% distance from entry
  - Confidence clamped 10-95, horizon clamped 1-90 days
  - Risk/reward ratio computed from validated values
- **Input sanitization**: Raw data to LLMs goes through `validate_fundamentals()`/`validate_technical()`
- **Return clamping**: ±100% max on evaluated returns

### Deep Hardening: Track Record ✅ (Apr 13, 2026)
- **`_sf()` sanitizer**: All float values NaN/Inf-safe before metrics computation
- **Data quality field**: `data_quality.status` (good/insufficient/no_data), `closed_count`, `stale_open_signals`, `zero_return_closed`
- **Return sanitization**: All `return_pct` values sanitized upfront before any calculation

### Portfolio Analytics Dashboard ✅
- Sector allocation pie charts, P&L bar chart, Risk radar
- Risk metrics table, 5-Year Backtest Evidence, Forward Simulation Engine

## Architecture
```
/app/backend/
  server.py                       # FastAPI entry (~90 lines)
  routes/ (7 modules)
  daemons/ (2 modules)
  services/
    portfolio_engine.py           # HARDENED v3 — 6-stage pipeline
    portfolio_hardening.py        # Validation, factor scoring, constraints, backtesting
    portfolio_simulation.py       # LSTM + Monte Carlo forward simulation
    full_market_scanner.py        # HARDENED — timeouts, sanitization, factor scoring
    signal_service.py             # HARDENED — code-enforced signal bounds
    performance_service.py        # HARDENED — NaN-safe, data quality
    intelligence_engine.py, dashboard_service.py, etc.
/app/frontend/src/
  pages/
    PortfolioAnalytics.js         # Analytics + Backtests + Simulations
    BatchScanner.js               # HARDENED — timeout-safe polling
    SignalDashboard.js            # Signal tracking
    TrackRecord.js                # Performance history
    Watchlist.js, MarketOverview.js, etc.
```

## Backlog
- P1: Rebuild all 6 portfolios with hardened v3 pipeline (existing use v2)
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts (push notifications on rebalance/P&L threshold)
- Future: Walk-forward simulation (forward-tracking vs lookback validation)
- Future: Benchmark comparison dashboard

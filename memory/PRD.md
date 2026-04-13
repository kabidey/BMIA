# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst specializing in Indian Equity and Commodity markets with autonomous AI-managed portfolios backed by quantitative guardrails and historical evidence.

## What's Implemented

### Phase 1-10: Core Intelligence Platform ✅
- Market Cockpit, Symbol Analysis, God Mode 3-LLM, Full Market Scanner, Signal Tracking, BSE Guidance AI RAG, PDF Extraction, Autonomous Portfolio Engine

### Server Refactoring ✅ — server.py from 1200→90 lines, 7 route modules, 2 daemon modules

### Hardened God Mode Pipeline v3 ✅
**5 Quantitative Guardrails (code enforces, not LLM):**
1. Data Validation — Sanitizes yfinance garbage BEFORE LLM sees it
2. Sector Diversification — max 3 stocks per sector
3. Volatility-Based Sizing — Inverse ATR weighting
4. Quantitative Factor Scoring — Value/Quality/Growth/Momentum composite
5. Stop-Loss Enforcement — 8% hard stop + 20% auto-take-profit

### 5-Year Backtest Engine ✅
- CAGR, Sharpe, Max Drawdown, Alpha vs Nifty 50 | Cached 24h

### LSTM + Monte Carlo Forward Simulation ✅
- 2-layer LSTM + 10,000 GBM paths | VaR, CVaR, P(Profit) | 12h cache

### Deep Hardening: Batch Scanner ✅
- ThreadPoolExecutor (8s/stock), 120s LLM timeout, data sanitization, factor scoring

### Deep Hardening: AI Signals ✅
- Code-enforced signal bounds (targets, stops, confidence, R/R)

### Deep Hardening: Track Record ✅
- NaN/Inf-safe metrics, data quality field

### Portfolio v3 Rebuild ✅ (Apr 13, 2026)
- POST /api/portfolios/rebuild-all: Deletes all portfolios + caches, daemon auto-reconstructs with v3 pipeline
- Daemon updated with proper executor shutdown to prevent event loop issues
- bespoke_forward_looking constructed with v3 (10 stocks, volatility-based weights), 5 remaining auto-constructing

### Walk-Forward Simulation Tracking ✅ (Apr 13, 2026)
- GET /api/portfolios/walk-forward — all tracking records
- GET /api/portfolios/walk-forward/{strategy_type} — per-portfolio forecast vs actual
- Auto-creates first snapshot from simulation cache + live portfolio state
- Frontend: WalkForwardSection shows Forecast (MC Expected Return, P(Profit)) vs Actual (Live PnL, Portfolio Value) + Deviation

### Scanner History ✅ (Apr 13, 2026)
- Completed God Mode scans auto-saved to MongoDB (scanner_history collection)
- GET /api/batch/scan-history — expandable past scan records
- Frontend: ScannerHistory component with expandable cards showing full results table per scan
- Tracks scan_id, models_succeeded, pipeline stats, results_summary per scan

## Architecture
```
/app/backend/
  server.py                       # FastAPI entry (~90 lines)
  routes/ (7 modules)             # portfolios.py has rebuild-all + walk-forward
  daemons/ (2 modules)            # evaluation_scheduler, market_cache
  services/
    portfolio_engine.py           # v3 daemon with proper executor shutdown
    portfolio_hardening.py        # Validation, factor scoring, backtesting
    portfolio_simulation.py       # LSTM + Monte Carlo
    full_market_scanner.py        # Hardened with timeouts + sanitization
    signal_service.py             # Code-enforced signal bounds
    performance_service.py        # NaN-safe track record
/app/frontend/src/pages/
    PortfolioAnalytics.js         # Analytics + Backtests + Simulations + Walk-Forward + Rebuild v3 button
    BatchScanner.js               # God Mode Scanner + Scanner History
    SignalDashboard.js, TrackRecord.js, Watchlist.js, etc.
```

## MongoDB Collections
- portfolios, portfolio_backtests, portfolio_simulations
- walk_forward_tracking (NEW)
- scanner_history (NEW)
- signals, signal_evaluations, analyses

## Backlog
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts (push notifications)
- Future: Benchmark comparison dashboard (returns vs Nifty 50 ETF)

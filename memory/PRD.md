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
- **Results**: All 6 strategies show positive alpha vs Nifty 50

### Portfolio Analytics Dashboard ✅ (Apr 13, 2026)
- Sector allocation pie charts (global + per-portfolio)
- P&L comparison bar chart, Risk radar
- Risk metrics table (Beta, Volatility, Win%, Concentration, Pipeline version)
- 5-Year Backtest Evidence section with area charts and Nifty 50 benchmark

## Key Backtest Results (5Y Lookback)
| Strategy | CAGR | Alpha | Sharpe | Max DD |
|----------|------|-------|--------|--------|
| Bespoke Forward Looking | 52.4% | +41.7% | 2.43 | -5.2% |
| Quick Entry | 41.4% | +30.7% | 1.15 | -13.6% |
| Long Term Compounder | 32.9% | +22.2% | 2.05 | -7.5% |
| Alpha Generator | 32.4% | +20.8% | 1.25 | -7.5% |
| Value Stocks | 31.6% | +22.6% | 1.12 | -21.8% |
| Swing Trader | 12.4% | +6.3% | 0.41 | -9.5% |

## Architecture
```
/app/backend/
  server.py                       # FastAPI entry (~90 lines)
  routes/ (7 modules)
  daemons/ (2 modules)
  services/
    portfolio_engine.py           # HARDENED v3 — 6-stage pipeline with guardrails
    portfolio_hardening.py        # NEW — validation, factor scoring, constraints, backtesting
    intelligence_engine.py, full_market_scanner.py, dashboard_service.py, etc.
/app/frontend/src/
  pages/
    PortfolioAnalytics.js         # Analytics + 5Y Backtest Evidence
    Watchlist.js                  # Autonomous Portfolios with enriched data
```

## Backlog
- P1: Rebuild all 6 portfolios with hardened v3 pipeline (current portfolios use v2)
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Walk-forward strategy backtest (not just lookback)
- Future: Benchmark comparison dashboard (returns vs Nifty 50 ETF)

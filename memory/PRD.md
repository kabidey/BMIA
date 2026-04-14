# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst specializing in Indian Equity and Commodity markets with autonomous AI-managed portfolios backed by quantitative guardrails and historical evidence.

## What's Implemented

### Core Intelligence Platform ✅
- Market Cockpit, Symbol Analysis (25+ tech / 30+ fundamental), God Mode 3-LLM Scanner, AI Signal Dashboard, BSE Guidance RAG, PDF Extraction

### Server Refactoring ✅ — 7 route modules, 2 daemons

### Hardened God Mode Pipeline v3 ✅
- 5 code-enforced guardrails: data validation, sector diversification (max 3), ATR sizing, factor scoring, 8% stop-loss

### Deep Hardening ✅
- Batch Scanner: ThreadPoolExecutor, per-stock timeouts, 120s LLM cap
- AI Signals: code-enforced bounds on entry/target/stop-loss
- Track Record: NaN-safe metrics, data quality field

### 5-Year Backtest Engine ✅ — CAGR, Sharpe, Alpha vs Nifty 50, cached 24h

### LSTM + Monte Carlo Forward Simulation ✅ — 10K GBM paths, VaR, CVaR, P(Profit), cached 12h

### Portfolio v3 Rebuild ✅ — Manual construct via UI button, daemon disabled

### Walk-Forward Tracking ✅ — Forecast vs Actual snapshots

### Scanner History ✅ — Past God Mode scans cached and browsable

### Dedicated Portfolio Detail Pages ✅ — /portfolio/:type with holdings, sector pie, backtest, simulation, walk-forward inline

### Custom Portfolios ("Make Your Own") ✅
- Create up to 5 custom portfolios, 10 stocks each, ₹50L capital
- Stock search autocomplete (2400+ NSE), weight allocation, auto-balance
- Manual rebalancing with full change tracking (ADD/REMOVE/WEIGHT_CHANGE)
- 5Y backtest + LSTM/MC simulation computed per custom portfolio
- Tracking history with timestamped snapshots

### How It Works Documentation ✅ — 14-section exhaustive page

### TOTP 2FA Authentication ✅
- RFC 6238 TOTP (Google Authenticator compatible)
- Secret from TOTP_SECRET env var (no DB, no QR/secret exposure)
- JWT session, 1-hour expiry, 30s client-side expiry check, force logout
- Gate screen: 6-digit input, auto-submit, paste support

## Architecture
```
/app/backend/
  server.py, routes/ (8 modules incl custom_portfolios, totp_auth), daemons/, services/
/app/frontend/src/
  components/TOTPGate.js
  pages/ (11 pages)
```

## Env Vars (Production)
- TOTP_SECRET — 32-char base32 TOTP secret
- TOTP_JWT_SECRET — JWT signing key
- MONGO_URL, DB_NAME, EMERGENT_LLM_KEY, CORS_ORIGINS

## Backlog
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts, Benchmark comparison dashboard

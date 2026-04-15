# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst specializing in Indian Equity and Commodity markets with autonomous AI-managed portfolios backed by quantitative guardrails and historical evidence.

## What's Implemented

### Core Intelligence Platform
- Market Cockpit, Symbol Analysis (25+ tech / 30+ fundamental), God Mode 3-LLM Scanner, AI Signal Dashboard, BSE Guidance RAG, PDF Extraction

### Server Refactoring — 8 route modules, 2+ daemons

### Hardened God Mode Pipeline v3
- 5 code-enforced guardrails: data validation, sector diversification (max 3), ATR sizing, factor scoring, 8% stop-loss

### Deep Hardening
- Batch Scanner: ThreadPoolExecutor, per-stock timeouts, 120s LLM cap
- AI Signals: code-enforced bounds on entry/target/stop-loss
- Track Record: NaN-safe metrics, data quality field

### 5-Year Backtest Engine — CAGR, Sharpe, Alpha vs Nifty 50, cached 24h

### 4-Model ML Ensemble + Monte Carlo Forward Simulation
- LSTM, Attention-LSTM, GRU, GARCH
- 10K GBM paths, VaR, CVaR, P(Profit), cached 12h

### Portfolio v3 Rebuild — Manual construct via UI button, daemon with kill switch

### Walk-Forward Tracking — Forecast vs Actual snapshots

### Scanner History — Past God Mode scans cached and browsable

### Dedicated Portfolio Detail Pages — /portfolio/:type

### Custom Portfolios ("Make Your Own")
- Create up to 5 custom portfolios, 10 stocks each
- Manual rebalancing with full change tracking

### How It Works Documentation — 14-section exhaustive page

### OrgLens JWT Authentication
- Email -> OrgLens scan -> Password -> JWT (1h regular, 365d superadmin)

### Audit Log — Comprehensive tracking with superadmin UI

### DB-driven NSE Holiday Calendar

### 3-Month Rolling RAG Vectorization (Apr 2026)
- TF-IDF vectorization (25K+ vectors), cosine similarity search
- 90-day rolling window with automatic pruning

### Guidance Intelligence Briefing (Apr 2026)
- Auto-generated daily briefing with GPT-4.1 narrative
- Surfaces: critical filings, insider activity, AGMs, board meetings
- Frontend card on Market Cockpit

### Two-Stage Guidance AI Pipeline (Apr 2026)
- GPT-4.1 analyzes RAG data → Gemini 2.5 Flash restructures output

### Portfolio Detail Enhancements (Apr 2026)
- XIRR Calculation, P&L Breakdown, Win Rate
- Portfolio Rationale (thesis, risk assessment, data quality)
- Rebalance History with empty state

### Screener.in-Style Stock Documents (Apr 2026)
- Per-stock documents view: Announcements, Important, Board Meetings, Insider/SAST, AGM/EGM, Credit Ratings, Annual Reports
- Tabbed category navigation, search, PDF links
- BSE external link per stock
- Endpoint: GET /api/guidance/stock/{symbol}/documents

## Architecture
```
/app/backend/
  server.py, routes/ (11 modules), daemons/, services/
  services/vector_store.py, briefing_service.py, guidance_ai_service.py
/app/frontend/src/
  pages/Guidance.js (StockDocuments, DocItem components)
  pages/MarketOverview.js (GuidanceBriefingCard)
  pages/PortfolioDetail.js (XirrSection, ConstructionNotes)
```

## Backlog
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts
- Future: Benchmark comparison dashboard
- Refactor: Rename TOTPGate.js -> AuthGate.js

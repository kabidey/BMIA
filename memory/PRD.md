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
- LSTM, Attention-LSTM, GRU, GARCH models
- 10K GBM paths, VaR, CVaR, P(Profit), cached 12h

### Portfolio v3 Rebuild — Manual construct via UI button, daemon with kill switch

### Walk-Forward Tracking — Forecast vs Actual snapshots

### Scanner History — Past God Mode scans cached and browsable

### Dedicated Portfolio Detail Pages — /portfolio/:type with holdings, sector pie, backtest, simulation, walk-forward

### Custom Portfolios ("Make Your Own")
- Create up to 5 custom portfolios, 10 stocks each, Rs 50L capital
- Stock search autocomplete (2400+ NSE), weight allocation, auto-balance
- Manual rebalancing with full change tracking
- 5Y backtest + LSTM/MC simulation per custom portfolio

### How It Works Documentation — 14-section exhaustive page

### OrgLens JWT Authentication
- Email -> OrgLens scan -> Password -> JWT (1h regular, 365d superadmin)
- Superadmin: somnath.dey@smifs.com

### Audit Log — Comprehensive tracking with superadmin UI

### DB-driven NSE Holiday Calendar and Market Session Intelligence

### 3-Month Rolling RAG Vectorization (Apr 2026)
- TF-IDF vectorization using sklearn (25,000+ vectors: announcements + PDF chunks)
- Cosine similarity search for semantic retrieval
- 90-day rolling window with automatic pruning
- Vector store built on startup, rebuilt after each scrape

### Guidance Intelligence Briefing (Apr 2026)
- Auto-generated daily briefing with LLM narrative (GPT-4.1)
- Surfaces: top 5 critical filings, insider activity (14d), upcoming AGMs/EGMs, recent board meetings
- Most active stocks by filing volume (7d)
- Cached in MongoDB (6h), regenerate-on-demand via API
- Frontend card on Market Cockpit with expandable details, alert badges, refresh button

## Architecture
```
/app/backend/
  server.py, routes/ (11 modules), daemons/, services/
  services/vector_store.py — TF-IDF vector store (GuidanceVectorStore)
  services/guidance_service.py — BSE scraper with 3-month retention
  services/guidance_ai_service.py — RAG pipeline using vector search
  services/briefing_service.py — Daily intelligence briefing generator
/app/frontend/src/
  components/TOTPGate.js (OrgLens Auth Gate)
  pages/MarketOverview.js (GuidanceBriefingCard component)
  pages/ (11+ pages)
```

## Env Vars (Production)
- TOTP_JWT_SECRET — JWT signing key
- ORGLENS_API_KEY — OrgLens employee verification
- MASTER_CODE — Superadmin master code
- MONGO_URL, DB_NAME, EMERGENT_LLM_KEY, CORS_ORIGINS

## Key API Endpoints
- POST /api/auth/verify-orglens — Employee verification
- POST /api/custom-portfolios — Create manual portfolio
- GET /api/audit-log — Superadmin only
- POST /api/portfolios/rebuild-all — Superadmin kill switch
- GET /api/guidance/vectors/stats — Vector store statistics
- POST /api/guidance/vectors/rebuild — Manual vector rebuild
- POST /api/guidance/prune — Prune old guidance data
- POST /api/guidance/ask — AI RAG query (vector-powered)
- GET /api/guidance/briefing — Daily intelligence briefing (cached 6h)
- POST /api/guidance/briefing/refresh — Force regenerate briefing

## Backlog
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts (push notifications on rebalance/P&L threshold)
- Future: Benchmark comparison dashboard
- Refactor: Rename TOTPGate.js -> AuthGate.js

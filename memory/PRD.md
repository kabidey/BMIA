# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst for Indian Equity and Commodity markets.

## What's Implemented (Latest: Apr 2026)

### Compliance — NotebookLM-style RAG over NSE/BSE/SEBI circulars (NEW, Apr 2026)
- Full page at `/compliance` + global quick-launch modal (sidebar button / `Ctrl+Shift+C`)
- 3 independent TF-IDF stores (one per source: NSE, BSE, SEBI) with adaptive `max_df` for small/large corpora
- Background ingestion daemon (`daemons/compliance_ingestion.py`) — polite crawling at ~1 req/2s, 15-minute cadence, idempotent on `(source, circular_no)`. In-memory PDF extraction via pdfminer.six — no PDFs persisted.
- RAG chat answered by Claude Sonnet 4.5 via `emergentintegrations` (`services/compliance_agent.py`), strict [CIT-N] citation format + `## Sources` list
- Frontend (`components/ComplianceResearchPanel.js`) — sources toggle, year filter, index stats card, suggested starter questions, inline citation chips, expandable source cards with URLs
- Endpoints under `/api/compliance`:
  - `POST /research` — RAG query (question + sources[] + year_filter + top_k)
  - `GET /stats` — per-source ready/chunk_count/circular_count
  - `GET /circulars` — list ingested circulars with filters + pagination
  - `POST /rebuild` — manual TF-IDF rebuild
  - `POST /ingest-now` — manual ingestion trigger

### Big Market — Koyfin-Style Global Dashboard
- 13 Indian indices, 15 global, 7 commodities, 7 currencies, 4 yields, Factor Grid, Stock Snapshot
- Endpoints: `GET /api/big-market/overview`, `GET /api/big-market/snapshot/{symbol}`

### Core Platform
- Market Cockpit, Symbol Analysis, God Mode Scanner (NSE+BSE 3400+ stocks), AI Signals, BSE Guidance RAG

### 4-Model ML Ensemble + Monte Carlo
- LSTM, Attention-LSTM, GRU, GARCH (12s/stock)

### Portfolio System
- 6 AI portfolios + Custom, XIRR, P&L, Rebalance History
- HONEST P&L baseline vs immutable `initial_capital`; rebalance swaps preserve capital, realize P&L on exits
- SafeJSONResponse strips NaN/Inf → null
- PMS auto-reinvest (strategy-aware NIFTY-500 picker, no idle cash) + Exit History UI
- Market hours guard (IST 09:30-15:15 Mon-Fri, excl. NSE holidays)

### RAG & Intelligence
- 3-Month TF-IDF vectorization (25K+ vectors) for BSE Guidance
- GPT-4.1 → Gemini 2.5 Flash pipeline
- Daily Guidance Briefing on Cockpit
- Screener.in-style per-stock documents

### Auth & Audit
- OrgLens JWT + global fetch interceptor, audit log

## Backlog
- P1: Enhance Big Market — Market Movers scatter, FII/DII flows, Earnings Calendar, PCR, Analyst Estimates, News
- P2: CSV/PDF portfolio export
- P2: WebSocket/SSE real-time Cockpit (replace polling)
- Future: Portfolio push-alerts on rebalance/P&L thresholds
- Future: Benchmark comparison dashboard
- Refactor: Rename TOTPGate.js → AuthGate.js


# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst for Indian Equity and Commodity markets.

## What's Implemented (Latest: Apr 2026)

### Compliance — NotebookLM-style RAG over NSE/BSE/SEBI circulars (NEW, Apr 2026)
- Full page at `/compliance` + global quick-launch modal (sidebar button / `Ctrl+Shift+C`)
- 3 independent TF-IDF stores (one per source: NSE, BSE, SEBI) with adaptive `max_df` for small/large corpora
- **Production-ready ingestion** (`daemons/compliance_ingestion.py`):
  - 3 independent worker threads (one per source), each maintaining its own state in MongoDB `compliance_ingestion_state`
  - **Phased crawl**: `backfill` (most-recent → 2010, gentle 5-day pace) → `live` (last-30-days incremental every 15 min)
  - Date-ranged fetchers (NSE `from_date/to_date`, BSE `strFromDate/strToDate`, SEBI listing parse)
  - Tight timeouts (connect=5s, read=10-15s) + per-cycle PDF cap (`COMPLIANCE_MAX_PDFS_PER_CYCLE=10`) keep each cycle <5 min
  - Auto-rebuild TF-IDF after 50 new chunks or cycle 1-2
  - Polite `COMPLIANCE_REQUEST_DELAY_SEC=3s` between HTTP calls; all tunables exposed via env vars
  - Silent no-ops surfaced as `errors_count++` + `last_error` so UI accurately shows blocked sources
- RAG chat answered by Claude Sonnet 4.5 via `emergentintegrations` (`services/compliance_agent.py`), strict [CIT-N] citation format + `## Sources` list
- **"Cite in report"** one-click export on every answer: copies publication-ready markdown to clipboard with citations remapped to sequential `[1][2]…` (order of first appearance) + a numbered bibliography (circular no, date, title, category, URL). Auto-strips the LLM's inline Sources block. Ready to paste into email/PDF/Word.
- **Progress UI** in Compliance page & modal:
  - Overall phase badge (BACKFILL / LIVE) + per-source progress bars (BACKFILLING / LIVE)
  - Honest `progress_pct` = distinct years ingested ÷ total years span (2010 → today)
  - Per-source: years_covered, doc count, oldest-ingested date
  - Total circulars, vector chunks, overall %
  - Last-error banner appears when a source is blocked
  - Auto-poll: every 10s in backfill, 60s in live
  - Force-sync button for manual trigger
- Endpoints under `/api/compliance`:
  - `POST /research` — RAG query (question + sources[] + year_filter + top_k)
  - `GET /stats` — rich progress payload (overall_phase, totals, per-source phase/progress/errors)
  - `GET /circulars` — list ingested circulars with filters + pagination
  - `POST /rebuild` — manual TF-IDF rebuild
  - `POST /ingest-now` — manual ingestion trigger

### Big Market — Koyfin-Style Global Dashboard
- 13 Indian indices, 15 global, 7 commodities, 7 currencies, 4 yields, Factor Grid, Stock Snapshot
- **Intel Tab (NEW, Apr 2026)** — 6 aggregators with zero data-source leakage in UI per user requirement:
  - Market Movers scatter (gainers/losers/high-volume, x=%chg y=vol z=traded-value)
  - Institutional Flows (FII/DII daily net cash + F&O contracts)
  - Earnings & Events calendar (NSE + BSE merged, configurable window)
  - Put-Call Ratio (Nifty + Bank Nifty OI-based with sentiment labels + expiry)
  - Analyst Estimates (CMP, P/E, ROE, Mcap, Book, Yield per ticker; live re-load)
  - Market News (multi-source RSS dedup, auto-refresh 5m)
- Endpoints: `GET /api/big-market/overview`, `/snapshot/{symbol}`, `/movers`, `/fii-dii`, `/earnings-calendar`, `/pcr`, `/analyst-estimates/{symbol}`, `/news`

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
- P2: CSV/PDF portfolio export
- P2: WebSocket/SSE real-time Cockpit (replace polling)
- P2: Exponential backoff in compliance_ingestion workers on repeated `no_data` cycles (BSE/SEBI are upstream-blocked from cloud IPs; errors_count grows unbounded today)
- Future: Portfolio push-alerts on rebalance/P&L thresholds
- Future: Benchmark comparison dashboard
- Future: Compliance "Save research" + Monday digest email
- Refactor: Rename TOTPGate.js → AuthGate.js


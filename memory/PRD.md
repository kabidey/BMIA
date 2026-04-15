# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst specializing in Indian Equity and Commodity markets with autonomous AI-managed portfolios backed by quantitative guardrails and historical evidence.

## What's Implemented

### Core Intelligence Platform
- Market Cockpit, Symbol Analysis (25+ tech / 30+ fundamental), God Mode 3-LLM Scanner, AI Signal Dashboard, BSE Guidance RAG, PDF Extraction

### God Mode Scanner — Now NSE + BSE
- Scans 3400+ stocks (NSE bhav copy + BSE Group A merged & deduped)
- 4-stage pipeline: Universe → Prefilter → Deep Features → God Mode LLM Ensemble
- 3-minute hard cap, per-stock timeouts, factor scoring

### 4-Model ML Ensemble + Monte Carlo
- LSTM, Attention-LSTM, GRU, GARCH + 10K GBM paths

### Portfolio System
- 6 AI-managed portfolios + Custom ("Make Your Own")
- XIRR, P&L Breakdown, Portfolio Rationale, Rebalance History
- Daemon v3 with UI kill switch

### 3-Month RAG Vectorization
- TF-IDF (25K+ vectors), cosine similarity, 90-day pruning
- GPT-4.1 → Gemini 2.5 Flash two-stage pipeline

### Guidance Intelligence Briefing
- Auto-generated daily briefing on Market Cockpit
- Screener.in-style per-stock documents view

### OrgLens JWT Authentication
- Email → OrgLens → Password → JWT

### Audit Log
- Captures user email from JWT (global fetch interceptor) + request body for auth endpoints
- Body cached BEFORE call_next() to prevent consumption

### Mobile Responsiveness
- How It Works: overflow-x-hidden, break-words, smaller badges on mobile
- All pages checked for mobile viewport compatibility

## Architecture
```
/app/backend/
  server.py, routes/ (11 modules), daemons/, services/
  services/full_market_scanner.py — NSE + BSE combined universe
  services/vector_store.py, briefing_service.py, guidance_ai_service.py
/app/frontend/src/
  App.js — Global fetch interceptor (JWT auto-attach)
  hooks/useApi.js — Also injects JWT
  pages/ (13+ pages)
```

## Key API Endpoints
- POST /api/auth/verify-orglens, POST /api/auth/login
- GET /api/portfolios, GET /api/portfolios/xirr/{type}
- POST /api/batch/god-scan — Full NSE+BSE scan
- GET /api/guidance/briefing, POST /api/guidance/ask
- GET /api/guidance/stock/{symbol}/documents
- GET /api/audit-log — Superadmin only

## Backlog
- P2: CSV/PDF export for portfolio reports
- P2: WebSocket/SSE for real-time Market Cockpit
- Future: Portfolio alerts, Benchmark comparison dashboard
- Refactor: Rename TOTPGate.js → AuthGate.js

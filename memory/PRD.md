# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst for Indian Equity and Commodity markets.

## What's Implemented (Latest: Apr 2026)

### Big Market — Koyfin-Style Global Dashboard (NEW)
- **Indian Indices**: 13 NSE indices (Nifty 50, Sensex, Bank Nifty, IT, Pharma, FMCG, Auto, Metal, Realty, Energy, Infra, PSU Bank, India VIX) — Price, Chg, %, Z-Score, 1Y%, YTD%, 52W Range, Volume
- **Global Indices**: 15 (S&P 500, Nasdaq, Dow, DAX, FTSE, Nikkei, Hang Seng, Shanghai, etc.)
- **Commodities**: 7 (Gold, Silver, WTI, Brent, Natural Gas, Copper, Aluminum)
- **Currencies**: 7 (USD/INR, EUR/INR, GBP/INR, JPY/INR, EUR/USD, GBP/USD, Bitcoin)
- **Yields**: 4 (US 3M, 5Y, 10Y, 30Y)
- **Factor Grid**: Value/Core/Growth × Large/Mid/Small (Indian sectoral)
- **Market Pulse**: Nifty 50 + India VIX at a glance
- **Performance Rankings**: 1Y return bar chart
- **Stock Snapshot**: Koyfin-style per-stock view (Chart, Key Data, Valuation, Capital Structure, Performance Returns)
- Endpoints: GET /api/big-market/overview, GET /api/big-market/snapshot/{symbol}

### Core Platform
- Market Cockpit, Symbol Analysis, God Mode Scanner (NSE+BSE 3400+ stocks), AI Signals, BSE Guidance RAG

### 4-Model ML Ensemble + Monte Carlo
- LSTM, Attention-LSTM, GRU, GARCH (optimized: 12s per stock)

### Portfolio System
- 6 AI portfolios + Custom, XIRR, P&L, Rebalance History

### RAG & Intelligence
- 3-Month TF-IDF vectorization (25K+ vectors)
- GPT-4.1 → Gemini 2.5 Flash pipeline
- Daily Guidance Briefing on Cockpit
- Screener.in-style per-stock documents

### Auth & Audit
- OrgLens JWT + global fetch interceptor
- Audit log with proper user tracking

## Backlog
- P2: CSV/PDF export, WebSocket/SSE
- Future: Portfolio alerts, Benchmark dashboard
- Refactor: Rename TOTPGate.js → AuthGate.js

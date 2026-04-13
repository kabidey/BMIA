# BMIA - Bharat Market Intel Agent

## Problem Statement
Build a Tier-1 Quant Analyst specializing in Indian Equity and Commodity markets. Process massive market data to provide high-conviction investment recommendations by synthesizing Technical, Fundamental, and Sentiment data using yfinance, nselib, real-time news scraping, and LLMs.

## Core Requirements
- Real-time market intelligence dashboard (Market Cockpit)
- Symbol analysis with 25+ technical and 30+ fundamental indicators
- AI-driven signal generation using LLMs
- God Mode: Multi-LLM consensus (OpenAI GPT-4.1 + Claude Sonnet + Gemini Flash)
- Full-market NSE scanner (2400+ stocks with pre-filtering)
- Signal tracking, evaluation, and performance reporting
- BSE Corporate Filings scraping with AI RAG analysis
- 6 Autonomous AI-managed portfolios with hardened screening & auto-rebalancing
- Portfolio analytics dashboard with sector allocation, risk metrics, performance comparison

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **APIs**: yfinance, nselib, bse, pdfplumber, Emergent LLM Key (OpenAI/Anthropic/Gemini)

## What's Implemented

### Phase 1-8: Core → AI → Cockpit → God Mode → Scanner → Guidance → RAG ✅
### Phase 9: PDF Extraction (Simplified) ✅
### Phase 10: Autonomous Portfolio Engine ✅
### Server Refactoring ✅ (Apr 13, 2026)
### Hardened God Mode Pipeline v2 ✅ (Apr 13, 2026)

### Full Portfolio Rebuild with Hardened Pipeline ✅ (Apr 13, 2026)
- All 6 portfolios deleted and reconstructed using hardened v2 pipeline
- Each portfolio: NSE Universe (2456) → Advanced Screener → Deep Enrichment → BSE Guidance → 3-LLM Consensus
- All holdings have: technical_signal, fundamental_grade, filing_insight, risk_flag, consensus_votes
- All 6 active: bespoke_forward_looking, quick_entry, long_term, swing, alpha_generator, value_stocks

### Portfolio Analytics Dashboard ✅ (Apr 13, 2026)
- New `/analytics` page with full sector allocation, risk metrics, performance comparison
- **Global Sector Allocation** pie chart (Recharts) showing all sectors across 6 portfolios
- **P&L by Strategy** horizontal bar chart comparing returns
- **Risk Radar** chart (beta vs win rate) when data available
- **Risk Metrics Table**: Strategy, Invested, Value, Return, Beta, Volatility, Win%, Top3 Concentration, Best/Worst performers, Pipeline version
- **Per-portfolio sector breakdowns** (6 individual pie charts)
- **Aggregate metrics**: Total Invested, Current Value, Total Return, P&L, Avg Beta, Active count

### Deployment Bug Fixes ✅ (Apr 13, 2026)
- Fixed `NoneType has no attribute 'upper'` — None guards in market_service
- Fixed `Out of range float values not JSON compliant` — NaN/Infinity sanitizer
- Fixed BSE API parameter change (`group` → `name`)

## Architecture
```
/app/backend/
  server.py                       # FastAPI entry (slim ~90 lines)
  routes/
    symbols.py, market.py, analysis.py, signals.py, guidance.py, bse.py, portfolios.py (+ analytics endpoint)
  daemons/
    evaluation_scheduler.py, market_cache.py
  services/
    portfolio_engine.py           # HARDENED v2 — 6-stage autonomous pipeline
    intelligence_engine.py, full_market_scanner.py, dashboard_service.py
    signal_service.py, guidance_service.py, guidance_ai_service.py
    pdf_extractor_service.py, bse_price_service.py, market_service.py
/app/frontend/src/
  pages/
    Watchlist.js                  # Autonomous Portfolios with enriched data
    PortfolioAnalytics.js         # NEW — Analytics dashboard
    MarketOverview.js, SymbolAnalysis.js, BatchScanner.js, etc.
  components/layout/
    Sidebar.js (8 nav items now), SignalAlerts.js, SearchCommand.js
```

## Key API Endpoints
- `GET /api/portfolios/overview` - All 6 portfolios summary
- `GET /api/portfolios/analytics` - Sector allocation, risk metrics, performance comparison
- `GET /api/portfolios/{type}` - Portfolio with enriched holdings
- `GET /api/portfolios/rebalance-log-all/recent` - Rebalance history
- `GET /api/market/cockpit` - Dashboard metrics
- `POST /api/batch/god-scan` - Full market scan
- `POST /api/guidance/ask` - BSE filings RAG

## Backlog
- P1: Monitor continuous rebalancing execution (daemon runs daily 4-6 PM IST)
- P2: WebSocket/SSE for real-time Market Cockpit streaming
- P2: CSV/PDF export for analysis/signals
- Future: Benchmark comparison (portfolio returns vs NIFTY 50)

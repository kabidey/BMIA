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
- Portfolio tracking with live BSE prices

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **APIs**: yfinance, nselib, bse, Emergent LLM Key (OpenAI/Anthropic/Gemini)

## What's Implemented

### Phase 1-3: Core POC → MVP → AI Integration ✅
- Market data retrieval via yfinance
- Technical analysis (25+ indicators)
- Fundamental analysis (30+ metrics)
- News scraping & sentiment analysis
- AI chat analysis (OpenAI)
- Bloomberg-terminal dark theme UI

### Phase 4: Advanced Quant & AI Batch Scanner ✅
- Intelligence engine with enriched LLM context
- AI batch scanning across sectors
- Signal generation with entry/targets/stop-loss
- Learning context from past signals

### Phase 5: Market Intelligence Cockpit ✅
- Major Indices (NSE/BSE live data)
- FII & DII Flows, India VIX, Advance/Decline
- Sectoral Heatmap, Volume Shockers
- Put-Call Ratio, OI Buildup, Corporate Actions

### Phase 6: God Mode & Full Market Scanner ✅
- Full NSE universe scanner (2400+ stocks)
- 3-LLM parallel consensus
- Background task pattern, Frontend polling
- Pipeline tracker UI

### Performance: Background Cache ✅
- Dashboard loads in ~2s (was 15-20s)

### Phase 7: Guidance — BSE Corporate Filings ✅
- Scrapes bseindia.com for Group A stocks
- 1,285+ announcements from 264+ stocks
- Filters, pagination, PDF download links
- Daily 5 AM IST scheduler

### Phase 8: Intelligent Guidance AI (RAG) ✅
- RAG pipeline: Question → Retrieve → Contextualize → LLM → Answer
- GPT-4.1 via Emergent LLM Key
- Source citations with filing references
- Conversation history for follow-ups

### Phase 9: New Features ✅ (Apr 13, 2026)
- **PDF Text Extraction**: Background daemon extracts text from BSE PDFs using pdfplumber, chunks for RAG
- **BSE Price Data**: Live quotes, gainers/losers, 52-week H/L, advance/decline via `bse` library
- **Portfolio & Watchlist**: Full CRUD with live BSE prices, P&L calculation, portfolio summary
- **Signal Alert Notifications**: Toast popups polling /api/signals/alerts for TARGET_HIT/STOP_LOSS_HIT

### Auto-Evaluation Scheduler ✅
- Background daemon auto-evaluates open signals every 60s

## Architecture
```
/app/backend/
  server.py                       # FastAPI main
  services/
    intelligence_engine.py        # God Mode multi-LLM
    full_market_scanner.py        # 2400+ stock scanning
    dashboard_service.py          # Market cockpit data
    signal_service.py             # Signal CRUD & evaluation
    guidance_service.py           # BSE scraper
    guidance_ai_service.py        # RAG analysis
    pdf_extractor_service.py      # PDF text extraction daemon
    bse_price_service.py          # BSE live prices
    watchlist_service.py          # Portfolio/watchlist
    ...
/app/frontend/src/
  pages/                          # MarketOverview, SymbolAnalysis, BatchScanner,
                                  # SignalDashboard, TrackRecord, Guidance, Watchlist
  components/layout/              # Sidebar, TerminalPanel, SignalAlerts, SearchCommand
  hooks/useApi.js                 # API layer
```

## Key API Endpoints
- `GET /api/market/cockpit` - Full dashboard metrics
- `POST /api/batch/god-scan` → `GET /api/batch/god-scan/{job_id}` - Batch scan
- `POST /api/signals/generate` → `GET /api/signals/generate-status/{job_id}` - God mode signal
- `GET /api/signals/active` / `GET /api/signals/history` / `GET /api/signals/alerts`
- `GET /api/guidance/stats` / `GET /api/guidance` / `POST /api/guidance/ask`
- `GET /api/guidance/pdf/stats` / `POST /api/guidance/pdf/process`
- `GET /api/bse/quote/{scrip_code}` / `GET /api/bse/gainers` / `GET /api/bse/losers`
- `GET /api/watchlist` / `POST /api/watchlist/add` / `DELETE /api/watchlist/{symbol}`
- `GET /api/watchlist/summary`

## Backlog
- P2: WebSocket/SSE for real-time streaming of Market Cockpit
- P2: CSV/PDF export for analysis/signals
- P3: Portfolio watchlist improvements (alerts for watchlist stocks)
- P3: server.py refactoring (move daemons to workers/ module)

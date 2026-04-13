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
- 6 Autonomous AI-managed portfolios with auto-rebalancing

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **APIs**: yfinance, nselib, bse, pdfplumber, Emergent LLM Key (OpenAI/Anthropic/Gemini)

## What's Implemented

### Phase 1-3: Core POC → MVP → AI Integration ✅
### Phase 4: Advanced Quant & AI Batch Scanner ✅
### Phase 5: Market Intelligence Cockpit ✅
### Phase 6: God Mode & Full Market Scanner ✅
### Performance: Background Cache ✅ (Dashboard ~2s load)
### Phase 7: Guidance — BSE Corporate Filings ✅
### Phase 8: Intelligent Guidance AI (RAG) ✅

### Phase 9: PDF Extraction (Simplified) ✅ (Apr 13, 2026)
- Background daemon extracts text from BSE PDFs using pdfplumber
- Text chunks stored INLINE with guidance docs (pdf_text_chunks field)
- No persistent PDF storage — PDF bytes flushed after extraction
- Download links point to bseindia.com
- RAG pipeline uses inline PDF text for deeper analysis

### Phase 10: Autonomous Portfolio Engine ✅ (Apr 13, 2026)
- 6 fully autonomous AI-managed portfolios:
  1. **Bespoke Forward Looking** — Future catalysts, 6-12 month horizon
  2. **Quick Entry** — Momentum breakouts, 1-4 week horizon
  3. **Long Term Compounder** — Blue-chip moat businesses, 2-5 year horizon
  4. **Swing Trader** — RSI oversold, mean reversion, 1-2 week horizon
  5. **Alpha Generator** — Contrarian undervalued picks, 3-6 month horizon
  6. **Value Stocks** — Deep value, Buffett-style, 1-3 year horizon
- Each portfolio: ₹50L initial capital, 10 stocks, God Mode 3-LLM consensus
- Pipeline: NSE Universe (2400+) → Strategy Pre-filter → Deep Features → 3-LLM Selection → Capital Allocation
- Continuous autonomous analysis via background daemon
- Auto-rebalancing after market close (4-6 PM IST) with full rationale
- Rebalance history log with incoming/outgoing stock rationale

### BSE Price Data ✅ (Apr 13, 2026)
- Live quotes via `bse` library (gainers, losers, 52-week H/L, advance/decline)

### Signal Alert Notifications ✅ (Apr 13, 2026)
- Toast popups for TARGET_HIT / STOP_LOSS_HIT via polling

### Auto-Evaluation Scheduler ✅

## Architecture
```
/app/backend/
  server.py                       # FastAPI main
  services/
    portfolio_engine.py           # Autonomous 6-portfolio engine
    intelligence_engine.py        # God Mode multi-LLM
    full_market_scanner.py        # 2400+ stock scanning
    dashboard_service.py          # Market cockpit cache
    signal_service.py             # Signal CRUD & evaluation
    guidance_service.py           # BSE scraper
    guidance_ai_service.py        # RAG analysis
    pdf_extractor_service.py      # Inline PDF text extraction
    bse_price_service.py          # BSE live prices
    ...
/app/frontend/src/
  pages/                          # MarketOverview, SymbolAnalysis, BatchScanner,
                                  # SignalDashboard, TrackRecord, Guidance, Watchlist (Portfolios)
  components/layout/              # Sidebar, SignalAlerts, SearchCommand
```

## Key API Endpoints
- `GET /api/portfolios/overview` - All 6 portfolios summary
- `GET /api/portfolios` - Full portfolio list with holdings
- `GET /api/portfolios/{type}` - Specific portfolio detail
- `POST /api/portfolios/{type}/refresh-prices` - Manual price refresh
- `GET /api/portfolios/rebalance-log-all/recent` - Rebalance history
- `GET /api/market/cockpit` - Dashboard metrics
- `POST /api/batch/god-scan` - Full market scan
- `GET /api/guidance/stats` / `POST /api/guidance/ask` - BSE filings + RAG
- `GET /api/bse/quote/{scrip_code}` - Live BSE prices

## Backlog
- P2: WebSocket/SSE for real-time Market Cockpit streaming
- P2: CSV/PDF export for analysis/signals
- P3: server.py refactoring (move daemons to workers/ module)

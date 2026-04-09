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

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Recharts
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **APIs**: yfinance, nselib, Emergent LLM Key (OpenAI/Anthropic/Gemini)

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
- numpy boolean JSON serialization fix

### Phase 5: Market Intelligence Cockpit ✅
- Major Indices (NSE/BSE live data)
- FII & DII Flows
- India VIX tracker
- Advance/Decline breadth
- Sectoral Heatmap
- Volume Shockers
- 52-Week High/Low Clusters
- Put-Call Ratio (PCR)
- Open Interest (OI) Buildup
- Corporate Actions/Block Deals

### Phase 6: God Mode & Full Market Scanner ✅
- Full NSE universe scanner (2400+ stocks via nselib bhav copy)
- Statistical pre-filtering pipeline
- 3-LLM parallel consensus (GPT-4.1 + Claude Sonnet + Gemini Flash)
- Background task pattern (prevents proxy timeout)
- Frontend polling for long-running scans
- God Mode toggle for single-stock analysis
- Pipeline tracker UI with stage progression
- Model votes & agreement level display
- Mobile responsive sidebar (hamburger menu)
- Removed "Made with Emergent" badge

### Performance: Background Cache ✅
- Background daemon thread pre-fetches cockpit data every 30s
- Slow modules (volume shockers, OI quadrant) refresh every 120s
- Market overview & heatmap cached with 60s TTL
- Dashboard loads in ~2s (was 15-20s)
- All API responses < 300ms from cache

## Architecture
```
/app/backend/
  server.py                    # FastAPI main
  services/
    intelligence_engine.py     # God Mode multi-LLM logic
    full_market_scanner.py     # 2400+ stock scanning
    dashboard_service.py       # Market cockpit data
    signal_service.py          # Signal CRUD & evaluation
    technical_service.py       # 25+ indicators
    fundamental_service.py     # 30+ metrics
    ...
/app/frontend/src/
  pages/                       # MarketOverview, SymbolAnalysis, BatchScanner, SignalDashboard, TrackRecord
  components/layout/           # Sidebar (responsive), TerminalPanel
  hooks/useApi.js             # API layer with polling for god mode
```

## Key API Endpoints
- `GET /api/market/cockpit` - Full dashboard metrics
- `POST /api/batch/god-scan` → `GET /api/batch/god-scan/{job_id}` - Background batch scan
- `POST /api/signals/generate` → `GET /api/signals/generate-status/{job_id}` - Background god mode signal
- `POST /api/signals/generate` (god_mode=false) - Synchronous signal
- `GET /api/signals/active` / `GET /api/signals/history`
- `POST /api/ai/chat` - AI analysis chat

## Backlog
- P1: Automated evaluation scheduler (cron/background task)
- P2: WebSocket/SSE for real-time streaming of Market Cockpit
- P2: CSV/PDF export for analysis/signals
- P3: BSE integration via bselib (currently unstable/timing out)
- P3: Portfolio tracking / watchlist persistence

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
- `server.py` reduced from ~1200 lines to ~90 lines
- Routes extracted to `/app/backend/routes/` (7 modules)
- Daemons extracted to `/app/backend/daemons/` (2 modules)

### Enhanced Portfolio UI ✅ (Apr 13, 2026)
- Tabbed Holdings / Rebalance History panels per portfolio
- SwapCard component for incoming/outgoing stock rationales

### Hardened God Mode Pipeline v2 ✅ (Apr 13, 2026)
- **Advanced Screener (screener.in inspired)**: Batch yfinance fundamental screening with strategy-specific criteria (P/E, P/B, ROE, D/E, revenue growth, profit margin)
- **6-Stage Pipeline**: Universe (2400+) → Liquidity → Advanced Screener → Deep Enrichment (25+ technicals + 30+ fundamentals) → BSE Guidance Integration → 3-LLM Consensus
- **BSE Guidance Integration**: Fetches recent BSE filings (board meetings, insider trading, results, corporate actions) for shortlisted stocks and includes them in LLM context
- **Anti-Hallucination Protocol**: LLMs instructed to only reference provided data, cite exact values, flag missing data
- **Strategy-Specific Rubrics**: Each of 6 strategies has a custom evaluation rubric (e.g., Value: Graham discount + earnings power + balance sheet safety + shareholder returns)
- **Consensus Voting**: Stocks picked by 2+ LLMs get priority; single-vote picks fill remaining slots
- **Enriched Holdings Data**: Each holding now has technical_signal (BULLISH/NEUTRAL/BEARISH), fundamental_grade (A/B/C/D), filing_insight, risk_flag, consensus_votes
- **Frontend Enhanced**: Holdings table shows signal badges, grade badges, AI Intelligence column with specific metric citations, BSE filing insights, risk flags

## Architecture
```
/app/backend/
  server.py                       # FastAPI entry (slim ~90 lines)
  routes/
    symbols.py, market.py, analysis.py, signals.py, guidance.py, bse.py, portfolios.py
  daemons/
    evaluation_scheduler.py, market_cache.py
  services/
    portfolio_engine.py           # HARDENED v2 — 6-stage autonomous pipeline
    intelligence_engine.py        # God Mode multi-LLM
    full_market_scanner.py        # 2400+ stock scanning
    dashboard_service.py, signal_service.py, guidance_service.py
    guidance_ai_service.py, pdf_extractor_service.py, bse_price_service.py
/app/frontend/src/
  pages/Watchlist.js              # Enhanced with signal badges, grades, filing insights
```

## Key API Endpoints
- `GET /api/portfolios/overview` - All 6 portfolios summary
- `GET /api/portfolios/{type}` - Portfolio with enriched holdings (technical_signal, fundamental_grade, filing_insight)
- `POST /api/portfolios/{type}/construct` - Trigger hardened construction
- `GET /api/portfolios/rebalance-log-all/recent` - Rebalance history
- `GET /api/market/cockpit` - Dashboard metrics
- `POST /api/batch/god-scan` - Full market scan
- `POST /api/guidance/ask` - BSE filings RAG

## Backlog
- P1: Rebuild remaining 5 portfolios with hardened pipeline v2 (currently only value_stocks uses it)
- P1: Monitor continuous rebalancing execution (daemon runs daily 4-6 PM IST)
- P2: WebSocket/SSE for real-time Market Cockpit streaming
- P2: CSV/PDF export for analysis/signals
- Future: Portfolio analytics dashboard (sector allocation, risk metrics)
- Future: Benchmark comparison (portfolio returns vs NIFTY 50)

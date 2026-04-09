# plan.md — Bharat Market Intel Agent (BMIA)

## 1. Objectives (updated)
- ✅ Prove the **core workflow** works with real data: **yfinance OHLCV + news (RSS) + LLM sentiment + technical/fundamental calculations → Alpha Score → recommendation**.
- ✅ Ship a V1 dashboard (FastAPI + React + MongoDB) for **NSE/BSE stocks + MCX commodity proxies** with charts, metrics, formulas, and SEBI disclaimers.
- ✅ Provide an **LLM-powered AI agent** (OpenAI/Claude/Gemini via Emergent universal key) for narrative analysis and Q&A.
- 🔜 VNext: harden data reliability (symbol issues, caching), expand universe, improve scanners/breakout logic, and add advanced UX (compare, exports, alerts).

---

## 2. Implementation Steps (Phases)

### Phase 1 — Core POC (Isolation) ✅ COMPLETED
**Goal:** Validate failure-prone integrations (yfinance India tickers + commodity proxies, scraping/RSS, LLM sentiment), then compute a stable Alpha Score.

**User stories (POC) — completed**
1. ✅ Input `RELIANCE.NS` → latest OHLCV + derived indicators.
2. ✅ Input commodity proxy (e.g., `GC=F`) → OHLCV + indicators.
3. ✅ Fetch headlines → sentiment score in `[-1, 1]`.
4. ✅ See Technical/Fundamental/Sentiment subscores + final Alpha Score.
5. ✅ Deterministic recommendation + SEBI-style disclaimer.

**Delivered artifacts**
- ✅ Single comprehensive POC test script: `/app/tests/test_core_poc.py`
- ✅ Fixed issues during POC:
  - `.env` newline issue for `EMERGENT_LLM_KEY`
  - Google News RSS query URL encoding

**Exit criteria — met**
- ✅ All 6 test blocks passed on 4 symbols (3 NSE stocks + 1 commodity proxy).

---

### Phase 2 — V1 App Development (MVP Dashboard) ✅ COMPLETED
**Goal:** Build full end-to-end product around the proven POC logic (no auth), with a Bloomberg-terminal-meets-modern-web UI.

**User stories (V1) — completed**
1. ✅ Search a stock/commodity and see Alpha Score + recommendation.
2. ✅ Candlestick + volume + RSI + MACD charts.
3. ✅ News feed + sentiment scoring.
4. ✅ Fundamental metrics + Graham intrinsic value (N/A-safe).
5. ✅ Both professional trading-style charts + lightweight charting where appropriate.

**Backend (FastAPI) — implemented**
- ✅ Core endpoints:
  - `GET /api/health`
  - `GET /api/symbols?q=` (autocomplete/search)
  - `POST /api/analyze-stock` (full single-symbol analysis)
  - `POST /api/batch/analyze` (scanner; neutral sentiment for speed)
  - `GET /api/market/overview` (gainers/losers)
  - `GET /api/market/heatmap` (sector grouped)
  - `POST /api/ai/chat` (LLM agent analysis; provider toggle)
  - `GET /api/analyses/history`
- ✅ Service modules:
  - `services/market_service.py` (yfinance OHLCV + caching)
  - `services/technical_service.py` (RSI, MACD, VSA, breakout heuristics)
  - `services/fundamental_service.py` (P/E, D/E, growth, Graham value)
  - `services/news_service.py` (yfinance news + Google News RSS fallback)
  - `services/sentiment_service.py` (LLM sentiment JSON)
  - `services/alpha_service.py` (weights + Sharpe + recommendation)
  - `services/ai_agent_service.py` (OpenAI/Claude/Gemini adapters)
- ✅ MongoDB integration for saving summary analysis rows.

**Frontend (React + shadcn/ui) — implemented**
- ✅ Pages:
  - Market Overview (gainers/losers, sector heatmap, tracked stocks table)
  - Symbol Analysis (tabs: Technical / Fundamental / News & Sentiment / AI Agent / Formulas)
  - Batch Scanner (sortable table + sector filter)
- ✅ Core components:
  - Alpha gauge (0–100)
  - Candlestick + volume (TradingView-style via `lightweight-charts`)
  - RSI + MACD charts (Recharts)
  - Fundamentals panel + Graham value
  - News feed with per-headline sentiment notes
  - Command palette search (Ctrl/Cmd+K)
  - SEBI disclaimers visible across pages
- ✅ Design system applied (dark-first, teal primary, semantic red/green), with typography and tokens defined in `index.css`.

**Fixes/patches applied during Phase 2**
- ✅ Fixed `lightweight-charts` runtime error by setting chart localization locale (`en-US`).
- ✅ Data reliability fix: yfinance symbol availability issue (e.g., `TATAMOTORS.NS` errors). Replaced with a valid symbol and improved resilience.

**Phase 2 testing — completed**
- ✅ Testing agent confirmation:
  - Backend: **100% (8/8 tests passed)**
  - Frontend: **95%** (expected 15–20s analysis wait; UI stable)
  - Integration: **100%** (yfinance + LLM + charts)
  - No critical bugs found

---

### Phase 3 — Add More Features + Hardening 🔜 NEXT
**Goal:** Expand coverage, improve scoring rigor, reduce flakiness, and add advanced analysis workflows.

**User stories (Expansion)**
1. Filter batch scanner by sector, market cap, volatility, alpha threshold.
2. Side-by-side symbol comparison (price/indicators/fundamentals/sentiment).
3. Explain breakout flags with levels + lookback windows + ATR compression.
4. Corporate actions (splits/dividends) adjustment and display.
5. Export analysis to PDF/CSV.

**Implementation focus**
- Breakout detection v2: multi-year consolidation detection (rolling highs/lows, ATR compression).
- VSA v2: spread/volume anomaly detection and effort-vs-result signals.
- Sector benchmarking: compute sector P/E medians from tracked universe (cache + periodic refresh).
- News hardening: add retry/backoff, selector fallback; prefer RSS.
- Caching/Perf: TTL tuning, background refresh jobs, rate-limit protection.
- Observability: structured logs, request IDs, endpoint latency.
- Optional: provider comparison for sentiment (OpenAI vs Claude vs Gemini).

**Phase 3 testing**
- Batch scan reliability, compare view, export correctness, corporate action adjustments.

---

### Phase 4 — Optional: Auth + Personalization (only after approval)
**User stories (Auth)**
1. Sign in and save watchlists.
2. Alerts when Alpha crosses thresholds.
3. Store preferred providers/timeframes.
4. Recent analyses history per user.
5. API usage / quotas per account.

---

## 3. Next Actions (immediate) (updated)
1. ✅ Phase 1 + Phase 2 already delivered.
2. 🔜 Phase 3 kickoff:
   - Add richer scanner filters + pagination
   - Implement compare view (2 symbols)
   - Improve breakout + VSA logic and explainability
   - Add export (CSV first)
3. 🔜 Data hardening:
   - Validate symbol list periodically; auto-disable yfinance-missing symbols
   - Improve caching and fallback behaviors

---

## 4. Success Criteria (updated)
- ✅ POC: For 3 stocks + 1 commodity proxy, produces complete JSON (indicators, fundamentals/N/A, sentiment, Sharpe, Alpha Score, recommendation).
- ✅ V1: `/api/analyze-stock` returns full analysis; UI renders gauge + charts + fundamentals + news + AI agent.
- ✅ Batch: Scanner returns a usable ranked list and is sortable/filterable (baseline).
- ✅ Reliability: Graceful degradation when yfinance/scraping/LLM fails (partial results + warnings).
- ✅ Compliance: SEBI-style disclaimers visible; recommendations framed as educational, not financial advice.

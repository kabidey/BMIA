# plan.md — Bharat Market Intel Agent (BMIA)

## 1. Objectives
- Prove the **core workflow** works with real data: **yfinance OHLCV + news scraping + LLM sentiment + indicator/fundamental calculations → Alpha Score → recommendation**.
- Ship a V1 dashboard (FastAPI + React + MongoDB + Polars) for **NSE/BSE stocks + MCX commodities** with charts, metrics, LaTeX formulas, and SEBI disclaimers.
- Provide an **LLM agent** (primary: OpenAI GPT; optional: Claude/Gemini) with tool calling: `get_market_snapshot`, `analyze_sentiment`, `calculate_alpha_score`.

---

## 2. Implementation Steps (Phases)

### Phase 1 — Core POC (Isolation) (must pass before app build)
**Goal:** Validate the failure-prone integrations: yfinance (India tickers + MCX proxies), scraping, and LLM sentiment; then compute a stable Alpha Score.

**User stories (POC)**
1. As a user, I can input `RELIANCE.NS` and get latest OHLCV + derived indicators.
2. As a user, I can input a commodity symbol (e.g., `GC=F` proxy) and get OHLCV + indicators.
3. As a user, I can fetch headlines for a symbol and see a sentiment score in `[-1, 1]`.
4. As a user, I can see Technical/Fundamental/Sentiment subscores and final Alpha Score.
5. As a user, I receive a deterministic recommendation (Strong Buy/Neutral/Sell) with disclaimers.

**Steps**
- Websearch best practices (quick):
  - yfinance for NSE/BSE tickers + fundamentals availability limits.
  - Reliable scraping approach (RSS where possible, fallback HTML selectors, request headers, retries).
  - Prompting pattern for consistent sentiment scoring JSON.
- Create standalone Python scripts (no web app yet):
  - `poc_market_data.py`: fetch OHLCV (1d/1h), volume, returns; validate NSE/BSE tickers.
  - `poc_indicators.py`: compute RSI, MACD, basic breakout detection, VSA heuristics.
  - `poc_fundamentals.py`: pull P/E, sector proxy (if missing, fallback to index/industry averages), Debt/Equity, revenue growth; compute Graham value `V=sqrt(22.5*EPS*BVPS)` with graceful N/A.
  - `poc_news_scrape.py`: fetch headlines (Moneycontrol/ET RSS if available; else HTML scrape) with dedupe.
  - `poc_llm_sentiment.py`: call OpenAI (primary) for sentiment; verify strict JSON `{score, rationale, keywords}`.
  - `poc_alpha.py`: compute Sharpe, momentum, weighted alpha: `0.4*T + 0.4*F + 0.2*S`.
- Define scoring rubric (MVP): normalize each subscore to 0–100; document fallback rules.
- Exit criteria: run POC for 3 tickers + 1 commodity, produce stable JSON output and consistent recommendations.

---

### Phase 2 — V1 App Development (MVP dashboard)
**Goal:** Build working end-to-end app around proven POC logic (no auth).

**User stories (V1)**
1. As a user, I can search a stock/commodity and instantly see the Alpha Score + recommendation.
2. As a user, I can view candlestick + RSI + MACD charts for a selected timeframe.
3. As a user, I can read the latest scraped headlines with per-headline sentiment and overall score.
4. As a user, I can see fundamental metrics + Graham value with N/A handling and tooltips.
5. As a user, I can switch between “Lightweight charts” and “Trading-style charts”.

**Backend (FastAPI)**
- Implement endpoints:
  - `GET /symbols` (searchable list: Nifty50 + key MCX proxies)
  - `POST /analyze-stock` (single symbol analysis; returns full analysis JSON)
  - `POST /batch/analyze` (Nifty50 batch; cached)
  - `GET /market/heatmap` (top movers/alpha leaders)
- Implement tool functions (internal modules mirroring POC):
  - `get_market_snapshot(symbol, period, interval)`
  - `analyze_sentiment(symbol, headlines)`
  - `calculate_alpha_score(technical, fundamental, sentiment, sharpe)`
- Data processing: Polars for indicator pipelines; caching (in-memory + Mongo) to reduce yfinance calls.
- Store results in MongoDB: `analyses`, `news_cache`, `symbols`, `runs`.

**AI Agent (LLM tool calling)**
- Primary: OpenAI GPT via Emergent key; configure optional Claude/Gemini adapters.
- Agent prompt: outputs structured recommendation + risk notes; can call tools for missing parts.

**Frontend (React)**
- Pages:
  - Market Overview (heatmap + leaders/laggards)
  - Single Symbol Analysis (tabs: Technical / Fundamental / News / Agent View)
  - Batch Scanner (Nifty50 table with filters)
- Visuals:
  - Alpha gauge (0–100) + thresholds (Strong Buy >85, Neutral 40–60, Sell <30)
  - LaTeX formulas rendering (Momentum, Graham, Sharpe, Alpha)
  - Charts: lightweight (Recharts) + trading-style (TradingView widget or similar)
- UX states: loading, partial data, rate-limit/backoff messaging.
- Always-visible SEBI-style disclaimer and “not investment advice”.

**Phase 2 testing (1 full E2E round)**
- Run end-to-end: search → analyze → charts render → headlines + sentiment → recommendation.
- Validate N/A fallbacks, caching, and error paths (scrape fail, yfinance fail, LLM fail).

---

### Phase 3 — Add More Features + Hardening
**Goal:** Expand coverage and improve reliability/quality.

**User stories (Expansion)**
1. As a user, I can filter the batch scanner by sector, market cap, volatility, and alpha threshold.
2. As a user, I can compare two symbols side-by-side (price, indicators, fundamentals, sentiment).
3. As a user, I can inspect why a stock is “breakout flagged” (levels + lookback window).
4. As a user, I can view corporate actions (splits/dividends) impacting price series.
5. As a user, I can export analysis to PDF/CSV.

**Implementation**
- Breakout detection v2: multi-year consolidation detection (rolling highs/lows + ATR compression).
- VSA v2: spread/volume anomalies, effort-vs-result heuristics.
- Sector P/E benchmarking: build sector mapping table; compute rolling medians from tracked universe.
- News scraping hardening: selector fallback, RSS preference, retries, robots compliance.
- LLM multi-provider toggle in UI; compare sentiments across providers (optional).
- Observability: structured logs, request IDs, latency metrics.

**Phase 3 testing (1 full E2E round)**
- Batch scan reliability, compare view, export, corporate action adjustments.

---

### Phase 4 — Optional: Auth + Personalization (only after user approval)
**User stories (Auth)**
1. As a user, I can sign in and save a watchlist.
2. As a user, I can set alerts when Alpha crosses thresholds.
3. As a user, I can store my preferred timeframes/providers.
4. As a user, I can see my recent analyses history.
5. As a user, I can manage API usage limits per account.

---

## 3. Next Actions (immediate)
1. Create POC scripts for yfinance (NSE/BSE + commodity proxies) and validate 4 symbols.
2. Implement indicator + fundamental extraction with strict fallback rules.
3. Implement scraping (RSS-first) + LLM sentiment JSON contract.
4. Finalize Alpha normalization + thresholds; lock output schema.
5. Only after POC passes: scaffold FastAPI + React + Mongo and wire `/analyze-stock`.

---

## 4. Success Criteria
- POC: For 3 stocks + 1 commodity, produces complete JSON with: indicators, fundamentals (or N/A), sentiment, Sharpe, Alpha Score, and recommendation.
- V1: `/analyze-stock` returns in <5–10s first-hit and <2s cached; UI renders charts + formulas + news.
- Batch: Nifty50 scan completes with caching and shows sortable table + heatmap.
- Reliability: Graceful degradation when scraping/LLM fails (still returns partial analysis + warnings).
- Compliance: SEBI-style disclaimers visible; recommendation phrasing includes risk context and “not financial advice”.

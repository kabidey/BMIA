# plan.md — Bharat Market Intel Agent (BMIA)

## 1. Objectives (updated)
- ✅ Ship a working V1 dashboard for Indian markets using real data: **yfinance OHLCV + RSS news + LLM sentiment + technical/fundamental panels**.
- ✅ Provide a combined scoring output (Alpha Score) and UI scaffolding (overview, analysis, scanner, AI chat).
- ✅ **Intelligence Revamp (north star achieved):** evolve BMIA from “formula-based scoring” to a **multi-input intelligence system** that:
  - produces **AI-generated, actionable signals** (`BUY/SELL/HOLD/AVOID`) with **entry, targets, stop-loss, timeframe, horizon, confidence, risk/reward & invalidators**
  - maintains an **auditable recommendation history** (stored in MongoDB)
  - **evaluates outcomes over time** (target/stop/expiry) and computes returns/drawdown
  - **learns from mistakes** via a closed-loop “post-mortem → learning context → improved next prompt” mechanism
  - exposes **Signal Dashboard + Track Record** with key performance metrics (win rate, expectancy, profit factor, streaks, sector/confidence breakdown)
- ✅ Maintain **SEBI-style disclaimers** and “educational only / not investment advice” framing everywhere.
- 🔜 **Phase 4 objective (in progress):** deepen quant inputs and remove remaining “formula-first” paths by:
  - wiring **25+ technical indicators + 30+ fundamental metrics** into the Intelligence Engine prompts
  - converting Batch Scanner from alpha-ranking to **AI-powered relative ranking**
  - revamping SymbolAnalysis and BatchScanner UI to surface expanded metrics and reduce redundancy

---

## 2. Implementation Steps (Phases)

### Phase 1 — Core POC (Isolation) ✅ COMPLETED
**Goal:** Validate the failure-prone integrations (yfinance India tickers + commodity proxies, RSS fallback, LLM sentiment) and produce stable JSON outputs.

**User stories (POC) — completed**
1. ✅ Input NSE ticker (e.g., `RELIANCE.NS`) → OHLCV + indicators.
2. ✅ Input commodity proxy (e.g., `GC=F`) → OHLCV + indicators.
3. ✅ Fetch headlines → sentiment score in `[-1, 1]`.
4. ✅ Compute subscores + Alpha Score.
5. ✅ Deterministic recommendation + disclaimer.

**Delivered artifacts**
- ✅ `/app/tests/test_core_poc.py`

**Exit criteria — met**
- ✅ All 6 test blocks passed on 4 symbols.

---

### Phase 2 — V1 App Development (MVP Dashboard) ✅ COMPLETED
**Goal:** Build an end-to-end dashboard around the validated POC pipeline.

**Delivered (V1)**
- ✅ Backend (FastAPI): analysis endpoints, market overview, heatmap, batch scan, AI chat.
- ✅ Frontend (React + shadcn/ui): Market Overview, Symbol Analysis (tabs), Batch Scanner.
- ✅ Professional charting: `lightweight-charts` for candlesticks + Recharts for RSI/MACD.
- ✅ LLM provider support: OpenAI/Claude/Gemini via Emergent universal key.
- ✅ SEBI disclaimers.

**Testing**
- ✅ Backend 100% (8/8), Integration 100%, Frontend core flows validated.

---

### Phase 3 — Intelligence Revamp (Multi-input AI Signals + Learning Loop) ✅ COMPLETED
**Goal:** Replace the “formula-only recommendation” with an **AI decision engine** that uses raw multi-input signals, generates trade-like signals, tracks them over time, evaluates correctness, and continuously improves.

#### 3.1 New Concepts & Output Contracts (implemented)
**Signal (canonical schema)**
- `_id`, `symbol`, `created_at/updated_at/closed_at`, `provider`, `model`
- `action`: `BUY | SELL | HOLD | AVOID`
- `timeframe`: `INTRADAY | SWING | POSITIONAL` + `horizon_days`
- `entry`: `{ type: market/limit, price, rationale }`
- `targets`: `[{ price, probability, label }]` (supports multiple)
- `stop_loss`: `{ price, type: hard/trailing, rationale }`
- `confidence`: `0–100`
- `key_theses`: bullets referencing provided data only
- `invalidators`: conditions that invalidate the thesis
- `risk_reward_ratio`, `position_sizing_hint`, `sector_context`, `detailed_reasoning`
- Tracking fields: `status`, `entry_price`, `current_price`, `return_pct`, `peak_return_pct`, `max_drawdown_pct`, `days_open`

**Evaluation schema**
- `signal_evaluations`: records closed outcomes with `status`, `return_pct`, `drawdown`, `days_open`, and notes.

#### 3.2 Backend Architecture Changes (implemented)
**New services added**
- ✅ `services/intelligence_engine.py`
  - gathers **raw** OHLCV + indicator series + fundamentals + headlines + sentiment + alpha snapshot
  - injects **learning context**
  - calls LLM with strict JSON schema for signal generation
- ✅ `services/signal_service.py`
  - stores signals, returns active/history
  - evaluates against current prices (target/stop/expiry)
  - logs evaluations into `signal_evaluations`
- ✅ `services/learning_service.py`
  - aggregates outcomes and generates: win rate, avg return, recent mistakes, lessons
  - stores `learning_context` (global) and serves it to the intelligence engine
- ✅ `services/performance_service.py`
  - computes track record: win rate, avg return, expectancy, profit factor, streaks
  - equity curve + breakdowns by sector/action/confidence

**MongoDB collections (implemented)**
- ✅ `signals`
- ✅ `signal_evaluations`
- ✅ `learning_context`
- ✅ (kept) `analyses` for prior snapshots/history

**New endpoints (implemented)**
- ✅ `POST /api/signals/generate` — generate & persist multi-input AI signal
- ✅ `GET /api/signals/active` — open signals + live P&L
- ✅ `GET /api/signals/history` — signal history (filters supported)
- ✅ `POST /api/signals/evaluate` — evaluate one signal (optional current_price)
- ✅ `POST /api/signals/evaluate-all` — batch evaluate all open signals
- ✅ `GET /api/signals/track-record` — performance metrics + equity curve
- ✅ `GET /api/signals/learning-context` — lessons learned + mistakes + calibration stats

#### 3.3 Intelligence Flow (Closed Loop) (implemented)
1. ✅ **Collect data**: OHLCV, indicator series, key levels, fundamentals, recent news, sentiment.
2. ✅ **Retrieve learning context**: past mistakes/successes + summary stats.
3. ✅ **LLM signal generation**: strict JSON schema + “no fabrication” constraints.
4. ✅ **Persist signal**: store in `signals`.
5. ✅ **Evaluate over time**: update status/returns; write to `signal_evaluations` when closed.
6. ✅ **Learn**: update `learning_context` from outcomes; inject it into subsequent generations.

> Note: This is “learning” via **prompt/context updates and guardrails**, not model fine-tuning.

#### 3.4 Frontend Revamp (implemented)
**New pages (added)**
- ✅ **Signal Dashboard** (`/signals`)
  - Active signals with live P&L
  - History view
  - AI Learning insights tab
  - “Evaluate All” action

- ✅ **Track Record** (`/track-record`)
  - KPI cards: win rate, expectancy, profit factor, avg win/loss, best/worst
  - Equity curve
  - Breakdown: sector performance + confidence calibration
  - Clear “No closed signals yet” state

**Symbol Analysis page updates (added)**
- ✅ Prominent **AI Intelligence Engine** section
- ✅ Multi-provider signal generation (`OpenAI/Claude/Gemini`)
- ✅ Full signal detail rendering: action banner, entry/targets/stop, theses, invalidators, detailed reasoning
- ✅ Learning context summary displayed with the signal

#### 3.5 Phase 3 Testing ✅ COMPLETED
**Testing results**
- ✅ Backend: **100%** (14/14)
- ✅ Frontend: **100%**
- ✅ Integration: **100%** (yfinance + LLM + MongoDB)

**Success criteria — met**
- ✅ AI-generated signals are structured and persisted with audit trail.
- ✅ System computes track record and learning context from stored outcomes.
- ✅ Learning context is used in subsequent signal generation.

---

### Phase 4 — Hardening + Advanced Quant Features (post-intelligence) 🚧 IN PROGRESS
**Goal:** Improve robustness, explainability, and quantitative depth now that the learning loop is stable.

#### 4.0 Current state (Phase 4 progress snapshot)
- ✅ Expanded quant inputs are already implemented at the data layer:
  - ✅ `services/technical_service.py`: **25+ indicators** (RSI, MACD, Bollinger, ADX, Stochastic, ATR, OBV, Williams %R, CCI, ROC, Ichimoku, Fibonacci, Pivot Points, expanded MAs incl. golden/death cross, price action)
  - ✅ `services/fundamental_service.py`: **30+ metrics** (PEG, EV/EBITDA, EV/Revenue, FCF yield, liquidity ratios, quarterly revenue/earnings, ownership, etc.)
  - ✅ Expanded symbol universe in `symbols.py` (NIFTY50 + Next50 + Midcap + MCX)
- 🔴 Remaining work: these expanded fields are **not yet fully consumed** by the Intelligence Engine prompt builder nor surfaced in scanner/UI.

#### 4.1 P0 — Wire expanded parameters into Intelligence Engine
**Goal:** Ensure AI signal generation uses the full depth of technical + fundamental inputs.

**Backend work**
- Update `services/intelligence_engine.py` context builder to include ALL new technical indicators:
  - Bollinger: upper/middle/lower, bandwidth, %B, squeeze, position
  - ADX: ADX value, +DI/-DI, trend_strength, direction
  - Stochastic: %K/%D, zone, crossover
  - ATR: ATR, ATR%, volatility label
  - OBV: OBV, OBV SMA20, trend
  - Williams %R, CCI, ROC
  - Ichimoku: tenkan/kijun, cloud signal, thickness, TK cross
  - Fibonacci: level map + nearest support/resistance
  - Pivot points: PP, S/R levels
  - Moving averages: SMA/EMA suite, above_all_ma, golden/death cross
  - Price action: last 5 candles, 20d/50d trend, daily change%
- Update `services/intelligence_engine.py` to include ALL expanded fundamentals:
  - valuation: PE/forward PE/PEG, P/S, P/B, EV/EBITDA, EV/Revenue, enterprise value
  - profitability: gross/operating/profit margins, ROE/ROA
  - growth: revenue growth, earnings growth, quarterly growth
  - balance-sheet & liquidity: debt/equity, debt/EBITDA, net cash, current/quick ratio
  - cashflow: FCF, operating cashflow, FCF yield
  - ownership/float/short: insider/institutional %, shares/float, short ratio
  - quarterly snapshots: last 4 quarters revenue & net income
- Prompt hygiene/robustness:
  - Keep “no fabrication” and strict JSON schema
  - Add explicit instruction: cite indicator names + values when making claims
  - Add guardrails for unreasonable entry/target/stop levels (sanity bounds checks)

**Acceptance criteria**
- For a test symbol, generated signal reasoning references expanded fields (e.g., “ADX 28 strong trend”, “Bollinger squeeze true”, “FCF yield X%”).
- No regression in `/api/signals/generate` latency beyond acceptable budget.

#### 4.2 P0 — Convert Batch Scanner to AI-powered ranking
**Goal:** Replace alpha-score-based ranking with AI-driven relative ranking using expanded metrics.

**Backend work**
- Add new endpoint: `POST /api/batch/ai-scan` (name final TBD) that:
  1. selects symbols (explicit list or sector)
  2. gathers market snapshot + expanded technicals + expanded fundamentals per symbol
  3. builds compact per-symbol summaries (to control prompt size)
  4. sends summaries to the LLM in a single prompt (batched) requesting:
     - ranking (1..N)
     - score (0–100)
     - action bias (BUY/SELL/HOLD/AVOID)
     - short rationale per symbol referencing provided metrics
  5. returns structured JSON to the frontend
- Performance strategy:
  - batch size (e.g., 8–12 symbols per LLM call) with iterative merging
  - caching results for a short TTL (optional) to reduce repeated costs

**Frontend work**
- Update BatchScanner page:
  - change copy from “Alpha Score ranking” → “AI-powered ranking”
  - sortable columns shift to: AI score, action bias, confidence (if provided), key metrics (price, change%, RSI)
  - keep sector filter and “Run Scan” workflow

**Acceptance criteria**
- Batch scan returns ranked results with a deterministic UI rendering.
- Results include AI score + short explanation per row.

#### 4.3 P1 — Frontend revamp (reduce redundancy, surface expanded data)
**Goal:** Make expanded technical/fundamental depth visible without clutter.

- Remove/retire Alpha Gauge from SymbolAnalysis UI (redundant vs AI signal section).
  - Ensure no broken imports (`AlphaGauge.js`) and adjust layout.
- SymbolAnalysis → Technical tab:
  - add “Advanced Indicators” cards/sections for: Bollinger, ADX, Stochastic, ATR/volatility, OBV trend
  - add “Key Levels” section for Fibonacci + Pivot points
  - show MA regime (above_all_ma, golden/death cross)
- SymbolAnalysis → Fundamental tab:
  - extend FundamentalsPanel to include EV multiples, PEG, FCF yield, liquidity, ownership
  - add quarterly mini-table (Revenue/Net Income last 4 quarters)
- Ensure design compliance:
  - maintain Bloomberg-like density with shadcn Cards/Tables
  - numeric fields use `font-mono tabular-nums`
  - no prohibited gradients/purple
  - keep SEBI disclaimer visible

#### 4.4 P1 — Update server wiring & remove legacy dependencies
**Goal:** Remove formula-first dependencies where they conflict with the Phase 4 direction.

- Update `server.py`:
  - add AI batch scan endpoint wiring
  - reduce/remove usage of `alpha_service` in batch scan path (alpha may remain for legacy display only, but should not drive ranking)
  - ensure `/api/analyze-stock` continues to return expanded technical/fundamental payloads for UI

#### 4.5 Testing & hardening (continuous)
- Add backend tests:
  - intelligence engine prompt/context builder includes new keys (snapshot test)
  - batch AI scan endpoint returns valid structured output
- Add smoke tests:
  - SymbolAnalysis renders new fields even when some metrics are missing
  - BatchScanner handles LLM errors gracefully (fallback state)

---

### Phase 5 — Optional: Auth + Personalization (only after approval)
- Login, per-user watchlists, saved signals, alert preferences
- Per-user track record + experiments (provider selection, aggressiveness)
- Personal risk profile: max risk per trade, time horizon preference

---

## 3. Next Actions (immediate) (updated)
1. **P0:** Update `intelligence_engine.py` to consume and render all expanded technical + fundamental metrics in the LLM context.
2. **P0:** Implement AI batch scan endpoint + update BatchScanner frontend to use AI ranking.
3. **P1:** Remove Alpha Gauge from SymbolAnalysis and surface advanced indicator panels.
4. **P1:** Extend FundamentalsPanel with EV/PEG/FCF/ownership + quarterly mini-table.
5. Testing: add prompt/context snapshot tests + scanner endpoint tests; run soak scan on NIFTY50 + MCX subset and monitor latency.

---

## 4. Success Criteria (updated)
- ✅ V1 remains functional (overview/analysis/scanner/chat).
- ✅ Phase 3 delivers (met):
  - AI-generated signals with entry/targets/stop/timeframe/confidence
  - persisted history + evaluation outcomes
  - track record dashboard with core metrics + equity curve
  - learning context that updates and is used for future signals
- ✅ Compliance: explicit disclaimers, no guarantees, transparent assumptions, no fabricated numbers.
- 🚧 Phase 4 success (in progress):
  - Intelligence Engine prompt includes ALL expanded technical + fundamental inputs.
  - Batch Scanner ranks using AI-powered relative analysis (not alpha score).
  - Frontend surfaces expanded indicators cleanly; Alpha Gauge removed without regressions.
  - Performance remains usable (batch scan completes within an acceptable time budget; graceful error handling).
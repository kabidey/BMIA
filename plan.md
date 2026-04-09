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
- ✅ **Phase 4 objective (COMPLETED):** deepen quant inputs and remove remaining “formula-first” paths by:
  - wiring **25+ technical indicators + 30+ fundamental metrics** into the Intelligence Engine prompts
  - converting Batch Scanner from alpha-ranking to **AI-powered relative ranking**
  - revamping SymbolAnalysis and BatchScanner UI to surface expanded metrics and reduce redundancy
  - expanding symbol universe and sector taxonomy (including commodities)

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

### Phase 4 — Hardening + Advanced Quant Features (post-intelligence) ✅ COMPLETED
**Goal:** Improve robustness, explainability, and quantitative depth now that the learning loop is stable.

#### 4.0 Completion snapshot (what shipped)
- ✅ Expanded quant inputs implemented and fully integrated end-to-end:
  - ✅ `services/technical_service.py`: **25+ indicators** (RSI, MACD, Bollinger, ADX, Stochastic, ATR, OBV, Williams %R, CCI, ROC, Ichimoku, Fibonacci, Pivot Points, expanded MAs incl. golden/death cross, price action)
  - ✅ `services/fundamental_service.py`: **30+ metrics** (EV/EBITDA, EV/Revenue, FCF yield, liquidity ratios, quarterly revenue/earnings, ownership, etc.)
  - ✅ Expanded symbol universe + sector taxonomy in `symbols.py` (e.g., NIFTY 50 + broader coverage + MCX commodities)

- ✅ Intelligence Engine rewrite:
  - ✅ `services/intelligence_engine.py` rewritten with `build_full_context()` to feed **all expanded technical + fundamental metrics** into LLM prompts
  - ✅ Added `build_batch_context()` + `generate_batch_ranking()` for batched, comparative AI ranking

- ✅ AI Batch Scanner conversion:
  - ✅ Added `POST /api/batch/ai-scan`
  - ✅ Replaced formula-based alpha ranking with AI-powered relative ranking (15 symbols per scan for performance)

- ✅ Frontend revamp:
  - ✅ Removed redundant `AlphaGauge` from SymbolAnalysis
  - ✅ Added expanded Technical panels (Bollinger, ADX, Stochastic, ATR, OBV, Williams %R, CCI, ROC, Ichimoku, Fibonacci, Pivot Points)
  - ✅ Rewrote BatchScanner UI for AI results (AI score, action, conviction, rationale)
  - ✅ Extended FundamentalsPanel with valuation multiples, profitability, growth, balance sheet, cash flow, risk/ownership, and quarterly mini-table

- ✅ Bug fix / hardening:
  - ✅ Fixed numpy JSON serialization (`numpy.bool_`, `np.integer`, `np.floating`) via `_sanitize()` in `technical_service.py`.

- ✅ Testing:
  - ✅ 100% pass rate (backend + frontend + integration)

#### 4.1 Phase 4 acceptance criteria — met
- ✅ AI signal reasoning references expanded indicators (e.g., ADX, Bollinger, FCF yield, EV multiples).
- ✅ Batch scan returns ranked results with AI score + rationale.
- ✅ AlphaGauge removed without broken imports or layout regressions.
- ✅ `/api/analyze-stock` returns a comprehensive, JSON-serializable payload.
- ✅ Performance remains usable (batch scan capped; graceful fallbacks present).

---

### Phase 5 — Optional: Auth + Personalization (only after approval)
- Login, per-user watchlists, saved signals, alert preferences
- Per-user track record + experiments (provider selection, aggressiveness)
- Personal risk profile: max risk per trade, time horizon preference

---

## 3. Next Actions (immediate) (updated)
**Phase 4 is complete.** Candidate next steps (pending approval):
1. **Phase 5 (optional):** Authentication + per-user watchlists/saved signals + alert preferences.
2. **Reliability hardening:** caching and rate limiting for yfinance + LLM endpoints; background jobs for batch scanning.
3. **Exports  scheduler:** CSV/PDF export and a scheduled daily scan (deferred earlier; can be added as a new phase).
4. **Cost/latency controls:** configurable batch size, provider defaults, and optional TTL caching for AI batch scan.

---

## 4. Success Criteria (updated)
- ✅ V1 remains functional (overview/analysis/scanner/chat).
- ✅ Phase 3 delivers:
  - AI-generated signals with entry/targets/stop/timeframe/confidence
  - persisted history + evaluation outcomes
  - track record dashboard with core metrics + equity curve
  - learning context that updates and is used for future signals
- ✅ Phase 4 delivers:
  - Intelligence Engine prompt includes ALL expanded technical + fundamental inputs.
  - Batch Scanner ranks using AI-powered relative analysis (not alpha score).
  - Frontend surfaces expanded indicators cleanly; Alpha Gauge removed.
  - Expanded symbol universe + sectors (incl. commodities) available.
  - Robust JSON serialization for all outputs.
- ✅ Compliance: explicit disclaimers, no guarantees, transparent assumptions, no fabricated numbers.

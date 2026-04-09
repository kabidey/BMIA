# plan.md — Bharat Market Intel Agent (BMIA)

## 1. Objectives (updated)
- ✅ Ship a working V1 dashboard for Indian markets using real data: **yfinance OHLCV + RSS news + LLM sentiment + technical/fundamental panels**.
- ✅ Provide an initial combined scoring output (Alpha Score) and UI scaffolding (overview, analysis, scanner, AI chat).
- 🔁 **Intelligence Revamp (new north star):** evolve BMIA from “formula-based scoring” to a **multi-input intelligence system** that:
  - produces **AI-generated, actionable signals** (BUY/SELL/HOLD) with **entry, target, stop-loss, timeframe, confidence**
  - maintains an **auditable recommendation history**
  - **evaluates outcomes** (win/loss, return, drawdown, hit target/stop/expiry)
  - **learns from mistakes** via a closed-loop “post-mortem → prompt/context updates” mechanism
  - exposes a **Track Record Dashboard** (win rate, avg return, expectancy, streaks, sector breakdown)
- ✅ Maintain **SEBI-style disclaimers** and “educational only / not investment advice” framing everywhere.

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

### Phase 3 — Intelligence Revamp (Multi-input AI Signals + Learning Loop) 🚧 CURRENT
**Goal:** Replace the “formula-only recommendation” with an **AI decision engine** that uses raw multi-modal inputs, generates trade-like signals, tracks them over time, evaluates correctness, and continuously improves.

#### 3.1 New Concepts & Output Contracts
**Signal (canonical schema)**
- `signal_id`, `symbol`, `created_at`, `provider`, `model`
- `action`: `BUY | SELL | HOLD | AVOID`
- `timeframe`: `INTRADAY | SWING | POSITIONAL` + `horizon_days`
- `entry`: `{ type: market/limit, price, rationale }`
- `targets`: `[{ price, probability }]` (at least 1)
- `stop_loss`: `{ price, type: hard/soft, rationale }`
- `confidence`: `0–100`
- `position_sizing_hint`: risk-based (educational), e.g. “risk 0.5–1% capital”
- `key_theses`: bullets referencing provided data only
- `invalidators`: what would prove the thesis wrong
- `risk_notes` + mandatory disclaimer

**Evaluation schema**
- `evaluation_id`, `signal_id`, `evaluated_at`
- `status`: `OPEN | HIT_TARGET | HIT_STOP | EXPIRED | INVALIDATED`
- `return_pct`, `max_drawdown_pct`, `days_open`
- `notes`: what worked/failed

#### 3.2 Backend Architecture Changes
Add new services:
- `services/intelligence_engine.py`
  - gathers **raw** OHLCV + indicator series + fundamentals + headlines + sentiment + market regime features
  - injects **learning context**
  - calls LLM with strict JSON schema for signal generation
- `services/signal_service.py`
  - CRUD for signals
  - normalization/validation of LLM output (bounds checks for targets/stops)
  - evaluation logic (target/stop/expiry rules)
- `services/learning_service.py`
  - aggregates historical outcomes
  - produces “lessons learned” + pattern library (what signals failed and why)
  - generates a compact **learning_context** blob for prompts
- `services/performance_service.py`
  - track record metrics: win rate, avg return, expectancy, sharpe-like signal metric, sector breakdown

MongoDB collections:
- `signals`
- `signal_evaluations`
- `learning_context` (versioned)
- (keep) `analyses` for snapshots

New/updated endpoints:
- `POST /api/signals/generate` (generate & persist a signal; returns structured signal JSON)
- `GET /api/signals/active` (open signals with live P&L)
- `GET /api/signals/history` (closed + open with filters)
- `POST /api/signals/evaluate` (evaluate one signal)
- `POST /api/signals/evaluate-all` (batch evaluate open signals)
- `GET /api/signals/track-record` (aggregated performance metrics)
- `GET /api/signals/learning-context` (current lessons + last updated)

Background jobs (lightweight):
- periodic evaluation runner (e.g., every X minutes/hours) to update open signals
- daily learning context refresh from the last N evaluations

#### 3.3 Intelligence Flow (Closed Loop)
1. **Collect data**: OHLCV (multi-timeframe), indicator series, key levels, fundamentals, recent news, sentiment.
2. **Compute regime features**: volatility percentile, trend strength, drawdown, volume anomalies.
3. **Retrieve learning context**: last N mistakes/successes + summary stats.
4. **LLM signal generation**: strict JSON schema + constraints.
5. **Persist signal**: store in `signals` with snapshot inputs hash.
6. **Evaluate over time**: update status & returns; write to `signal_evaluations`.
7. **Learn**: produce updated `learning_context` for the next signal generation.

> Note: This is “learning” via **prompt/context updates and guardrails**, not model fine-tuning.

#### 3.4 Frontend Revamp
New pages:
- **Signal Dashboard** (`/signals`)
  - Active signals table/cards with: symbol, action, entry, target(s), stop, days open, live return %, confidence
  - filters: action, timeframe, confidence, sector
  - signal detail drawer: reasoning, invalidators, evidence

- **Track Record** (`/track-record`)
  - win rate, avg return, expectancy, best/worst streak
  - charts: equity curve of signal outcomes, distribution of returns
  - breakdown: by sector, timeframe, confidence bands

Update Symbol Analysis page:
- add **“Generate AI Signal”** action
- display latest signal card with entry/target/stop overlay hints
- show “why this signal” evidence referencing raw inputs
- show “AI Learning Insights” panel (top mistakes + current guardrails)

#### 3.5 Phase 3 Testing (new)
Backend tests:
- signal generation returns valid schema and passes bounds checks
- signal persistence and retrieval
- evaluation correctness (target/stop/expiry)
- track record aggregates correctness

Frontend tests:
- generate signal flow
- active signals render + update
- track record renders

Success criteria for Phase 3:
- AI-generated signals are **structured, reproducible**, and stored with a full audit trail
- System can compute **track record** from stored signals
- Learning context is updated from outcomes and influences future signal outputs

---

### Phase 4 — Hardening + Advanced Quant Features (post-intelligence) 🔜 NEXT
**Goal:** Improve robustness and analytical quality once the intelligence loop is stable.
- Breakout detection v2 (multi-year consolidation + ATR compression)
- VSA v2 (effort vs result)
- Sector benchmarking from tracked universe
- Corporate actions adjustments
- Export (CSV/PDF)
- Compare view, alerts, watchlists

---

### Phase 5 — Optional: Auth + Personalization (only after approval)
- Login, watchlists, saved signals, alerts, provider preferences, per-user performance

---

## 3. Next Actions (immediate) (updated)
1. Implement backend Phase 3 services: `intelligence_engine.py`, `signal_service.py`, `learning_service.py`, `performance_service.py`.
2. Create MongoDB schemas/collections and migrations (soft).
3. Add endpoints for signal generation, evaluation, history, track record.
4. Add frontend pages: Signal Dashboard + Track Record; update Symbol Analysis to generate and display signals.
5. Add a periodic evaluator (server-side scheduled task) and daily learning-context refresh.
6. Run E2E tests and validate with a small universe (Nifty 10 + 2 commodities).

---

## 4. Success Criteria (updated)
- ✅ V1 remains functional (overview/analysis/scanner/chat).
- ✅ Phase 3 delivers:
  - AI-generated signals with entry/target/stop/timeframe/confidence
  - persisted history + evaluation outcomes
  - track record dashboard with core metrics
  - learning context that updates and is used for future signals
- ✅ Compliance: explicit disclaimers, no guarantees, transparent assumptions, no fabricated numbers.

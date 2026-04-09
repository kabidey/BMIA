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

- 🟦 **Phase 5 objective (NEW / approved): Market Intelligence Cockpit Dashboard Revamp**
  - Replace the existing “Market Overview” page with a **visual diagnostic cockpit** that highlights:
    - **liquidity flow** (institutional flows, volume shocks)
    - **market sentiment/regime** (VIX, breadth)
    - **sector rotation** (sector treemap + relative strength)
    - **derivatives positioning** (PCR + OI build-up quadrants)
    - **actionable events** (block/bulk deals + corporate actions)
  - **No Top Gainers/Losers** modules (explicitly removed).
  - Streaming/near-real-time feel via **auto-refresh (30–60s)** + **flash-on-change** microinteractions (no layout shift).

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
- ✅ `services/signal_service.py`
- ✅ `services/learning_service.py`
- ✅ `services/performance_service.py`

**MongoDB collections (implemented)**
- ✅ `signals`
- ✅ `signal_evaluations`
- ✅ `learning_context`
- ✅ (kept) `analyses`

**New endpoints (implemented)**
- ✅ `POST /api/signals/generate`
- ✅ `GET /api/signals/active`
- ✅ `GET /api/signals/history`
- ✅ `POST /api/signals/evaluate`
- ✅ `POST /api/signals/evaluate-all`
- ✅ `GET /api/signals/track-record`
- ✅ `GET /api/signals/learning-context`

#### 3.3 Intelligence Flow (Closed Loop) (implemented)
1. ✅ Collect data → 2. ✅ Retrieve learning context → 3. ✅ LLM generation → 4. ✅ Persist → 5. ✅ Evaluate → 6. ✅ Learn.

#### 3.4 Frontend Revamp (implemented)
- ✅ Signal Dashboard (`/signals`)
- ✅ Track Record (`/track-record`)
- ✅ Symbol Analysis page updated to render AI signals + learning context

#### 3.5 Phase 3 Testing ✅ COMPLETED
- ✅ Backend: 100% (14/14)
- ✅ Frontend: 100%
- ✅ Integration: 100%

---

### Phase 4 — Hardening + Advanced Quant Features (post-intelligence) ✅ COMPLETED
**Goal:** Improve robustness, explainability, and quantitative depth now that the learning loop is stable.

#### 4.0 Completion snapshot (what shipped)
- ✅ Expanded quant inputs integrated end-to-end:
  - ✅ `services/technical_service.py`: **25+ indicators**
  - ✅ `services/fundamental_service.py`: **30+ metrics**
  - ✅ Expanded symbol universe + sector taxonomy in `symbols.py`

- ✅ Intelligence Engine rewrite:
  - ✅ `build_full_context()` feeds all expanded technical + fundamental metrics
  - ✅ `generate_batch_ranking()` for comparative AI ranking

- ✅ AI Batch Scanner conversion:
  - ✅ Added `POST /api/batch/ai-scan`
  - ✅ Removed formula-based alpha ranking from scanner flow

- ✅ Frontend revamp:
  - ✅ Removed `AlphaGauge` from SymbolAnalysis
  - ✅ Added expanded Technical panels (Bollinger, ADX, Stochastic, ATR, OBV, Ichimoku, Fibonacci, Pivots, etc.)
  - ✅ Rewrote BatchScanner for AI results (AI score/action/conviction/rationale)
  - ✅ Extended FundamentalsPanel (valuation, growth, balance sheet, cash flow, ownership, quarterly table)

- ✅ Hardening:
  - ✅ Fixed numpy JSON serialization via `_sanitize()` in `technical_service.py`

- ✅ Testing:
  - ✅ 100% pass rate (backend + frontend + integration)

#### 4.1 Phase 4 acceptance criteria — met
- ✅ AI signal reasoning references expanded indicators.
- ✅ Batch scan returns ranked results with AI score + rationale.
- ✅ `/api/analyze-stock` returns comprehensive, JSON-serializable payload.

---

### Phase 5 — Market Intelligence Cockpit Dashboard Revamp 🟦 PLANNED
**Goal:** Turn the dashboard into a professional diagnostic tool for **liquidity flow, market regime, rotation, derivatives positioning, and actionable events**.

#### 5.0 Data sources confirmed (live)
- ✅ `nselib.capital_market.market_watch_all_indices()` — indices + breadth signals
- ✅ `nselib.capital_market.india_vix_data()` — India VIX
- ✅ `nselib.derivatives.fii_derivatives_statistics(trade_date)` — FII derivatives stats
- ✅ `nselib.derivatives.participant_wise_open_interest(trade_date)` — participant-wise OI
- ✅ `nselib.derivatives.nse_live_option_chain('NIFTY'|'BANKNIFTY')` — option chain → PCR
- ✅ `nselib.capital_market.block_deals_data(period/from/to)` — block deals feed
- ✅ `nselib.capital_market.corporate_actions_for_equity(from/to)` — dividends/splits/earnings actions
- ✅ `nselib.capital_market.week_52_high_low_report(trade_date)` — 52W high/low clusters
- ✅ `yfinance` — per-stock volume shockers/breakouts + sector aggregation

> Note: `xlrd>=2.0.1` installed to support nselib xls endpoints.

#### 5A — Backend: Dashboard API layer (P0)
**Goal:** Provide a single, efficient data contract for the cockpit with caching and predictable latency.

**Implementation**
- Add `services/dashboard_service.py` (new):
  - `get_indices_snapshot()` — Nifty 50, Sensex, Bank Nifty, Midcap 100, Smallcap 100
  - `get_market_breadth()` — Adv/Dec/Unch counts + A/D ratio
  - `get_vix_regime()` — latest VIX + short history
  - `get_flows_fii_dii()` — daily flows (primary: NSE; fallback: derivatives proxy if needed)
  - `get_sector_rotation()` — sector perf for treemap; includes relative strength vs Nifty
  - `get_volume_shockers_breakouts()` — 3–5x 10D avg volume AND price breakout filter
  - `get_52w_clusters()` — counts new highs vs lows + optional bucketization
  - `get_pcr()` — compute PCR for Nifty and Bank Nifty from option chain
  - `get_oi_quadrant()` — classify F&O symbols into 4 regimes (ΔPrice vs ΔOI)
  - `get_block_bulk_deals()` — block/bulk feed filtered by threshold
  - `get_corporate_actions()` — dividends/splits/earnings highlights (today/this week)

**Endpoints**
- Prefer **one consolidated endpoint** (recommended for dashboard):
  - `GET /api/market/cockpit` → returns `{ macro, micro, derivatives, actions, updated_at }`
- Optional granular endpoints (if needed for partial reload):
  - `/api/market/cockpit/macro`, `/micro`, `/derivatives`, `/actions`

**Non-functional**
- Add lightweight in-memory TTL cache (30–60s) to avoid hammering NSE endpoints.
- Strict JSON-serializable output (sanitize numpy/pandas types).
- Graceful degradation: if any module fails, return `module.error` but keep the rest.

**Exit criteria**
- Cockpit endpoint returns within ~2–5s typical.
- Works even if one data source fails.

#### 5B — Frontend: MarketOverview → Market Intelligence Cockpit (P0)
**Goal:** Replace current dashboard with a 4-section cockpit; “streaming” feel via auto-refresh + flash-on-change.

**Implementation**
- Replace `/pages/MarketOverview.js` layout with 4 stacked modules:

1) **Macro View (Market Weather)**
- **Major Indices Matrix** (streaming): Nifty 50, Sensex, Bank Nifty, Midcap100, Smallcap100
  - LTP, %Chg, abs chg, mini sparkline, day range
- **FII/DII Flows** bar chart (₹ Cr)
- **India VIX** gauge (speedometer)
- **Advance/Decline** ratio chip + progress/pie

2) **Micro View (Where the Action Is)**
- **Sector Treemap** (Recharts Treemap): size=market cap, color=intraday performance
- **Volume Shockers & Breakouts** table: only 3–5x avg volume + breakout trigger
- **52W clusters**: counts of new highs vs lows + buckets

3) **Derivatives & Sentiment (Smart Money Clues)**
- **PCR Gauges**: Nifty + BankNifty
- **OI Buildup Quadrant**: ScatterChart with 4 quadrants

4) **Corporate Actions & News**
- **Block/Bulk Deals feed** (filtered; threshold)
- **Corporate actions highlights** (dividends/splits/earnings actions)

**UX/Design rules** (from updated `design_guidelines.md`)
- Use `TerminalPanel` wrapper for every module.
- No top gainers/losers, no “noise” widgets.
- Streaming effect: flash-on-change (450ms) on updated cells; respect prefers-reduced-motion.
- Dense but scannable: mono numbers, short labels, compact charts.

**Controls**
- Auto-refresh toggle + interval selector (30s/60s/120s)
- Last updated timestamp per module

**Exit criteria**
- Above-the-fold shows: Indices matrix + flows/VIX/breadth.
- Treemap + shockers visible without excessive scrolling on 1920px.

#### 5C — Testing & Polish (P0)
- Backend tests:
  - cockpit endpoint shape validation
  - caching behavior and error isolation
- Frontend tests:
  - renders all 4 sections and key elements with `data-testid`
  - auto-refresh updates without layout shift

---

### Phase 6 — Optional: Auth + Personalization (only after approval)
- Login, per-user watchlists, saved signals, alert preferences
- Per-user track record + experiments (provider selection, aggressiveness)
- Personal risk profile: max risk per trade, time horizon preference

---

## 3. Next Actions (immediate) (updated)
1. **Phase 5A (Backend):** implement `GET /api/market/cockpit` + TTL caching + sanitization.
2. **Phase 5B (Frontend):** rewrite MarketOverview into the 4-section cockpit with streaming updates.
3. **Phase 5C:** add tests + polish (performance, responsive layout, reduced-motion).

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
- 🟦 Phase 5 delivers:
  - Market Overview replaced by **Market Intelligence Cockpit** (4-section diagnostic tool).
  - Live/streaming feel via auto-refresh and flash-on-change.
  - Dashboard emphasizes **liquidity flows, breadth, VIX regime, sector rotation, derivatives positioning, and actionable events**.
  - No Top Gainers/Losers modules.
  - All modules fail gracefully and remain performant.
- ✅ Compliance: explicit disclaimers, no guarantees, transparent assumptions, no fabricated numbers.

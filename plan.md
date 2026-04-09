# plan.md — Bharat Market Intel Agent (BMIA)

## 1. Objectives (updated)
- ✅ Ship a working V1 dashboard for Indian markets using real data: **yfinance OHLCV + RSS/news + LLM sentiment + technical/fundamental panels**.
- ✅ Provide UI scaffolding (cockpit dashboard, analysis, scanner, AI chat) + data services.
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

- ✅ **Phase 5 objective (COMPLETED): Market Intelligence Cockpit Dashboard Revamp**
  - Replaced the old “Market Overview” page with a **visual diagnostic cockpit** that highlights:
    - **liquidity flow** (institutional flows, volume shocks, block deals)
    - **market sentiment/regime** (VIX regime + breadth)
    - **sector rotation** (sector treemap)
    - **derivatives positioning** (PCR + quadrant view)
    - **actionable events** (block/bulk deals + corporate actions)
  - **No Top Gainers/Losers** modules.
  - Streaming/near-real-time feel via **auto-refresh (30–120s)** + **flash-on-change** microinteractions.
  - All data is live (**NSE India via nselib + Yahoo Finance via yfinance**), **no mocked APIs**.

- 🟡 **Phase 6 objective (NEW): God Mode Intelligence + Full-Market (Agnostic) Scanner**
  - Remove large-cap bias: scanner must be capable of scanning **all NSE EQ stocks (≈2450+)** and incorporate **BSE supplementation**.
  - Add **God Mode**: multi-LLM ensemble (OpenAI + Claude + Gemini) with **inter-LLM bouncing** and **consensus distillation**.
  - Scanner output optimized to surface **high-conviction BUY candidates** (not “gainers/losers”).
  - Keep performance and cost practical via **multi-stage filtering** (broad scan → quant prefilter → LLM ensemble on shortlist).

---

## 2. Implementation Steps (Phases)

### Phase 1 — Core POC (Isolation) ✅ COMPLETED
**Goal:** Validate failure-prone integrations (India tickers/commodities, news fallback, sentiment) and produce stable JSON outputs.

**Delivered artifacts**
- ✅ `/app/tests/test_core_poc.py`

---

### Phase 2 — V1 App Development (MVP Dashboard) ✅ COMPLETED
**Goal:** Build an end-to-end dashboard around the validated POC pipeline.

**Delivered (V1)**
- ✅ Backend (FastAPI): analysis endpoints, heatmap, batch scan, AI chat.
- ✅ Frontend (React + shadcn/ui): Market Overview, Symbol Analysis, Batch Scanner.

---

### Phase 3 — Intelligence Revamp (Multi-input AI Signals + Learning Loop) ✅ COMPLETED
**Goal:** Replace formula-only recommendation with AI decision engine + history + evaluation + learning.

**Key delivered concepts**
- ✅ Canonical Signal schema + evaluation schema
- ✅ MongoDB collections: `signals`, `signal_evaluations`, `learning_context`, `analyses`
- ✅ Endpoints: `/api/signals/*`

---

### Phase 4 — Advanced Quant Inputs + AI Batch Ranking ✅ COMPLETED
**Goal:** Increase quant depth + convert scanner away from Alpha Score.

**Completion snapshot**
- ✅ `technical_service.py`: 25+ indicators + JSON sanitization
- ✅ `fundamental_service.py`: 30+ metrics + quarterly data
- ✅ Intelligence engine expanded contexts for single-stock signals
- ✅ `POST /api/batch/ai-scan` + frontend scanner rewrite

---

### Phase 5 — Market Intelligence Cockpit Dashboard ✅ COMPLETED
**Goal:** Professional diagnostic cockpit.

**Backend**
- ✅ `services/dashboard_service.py`
- ✅ `GET /api/market/cockpit` + `GET /api/market/cockpit/slow`

**Frontend**
- ✅ `MarketOverview.js` rewritten into 4-section cockpit
- ✅ `TerminalPanel.js` layout wrapper

---

### Phase 6 — God Mode Intelligence & Full-Market Scanner 🟡 PLANNED / NEXT
**Goal:** Make the scanner **market-cap agnostic**, incorporate NSE+ BSE breadth, and produce **distilled BUY calls** using an LLM ensemble.

#### 6.0 Data Universe Expansion (NSE + BSE)
**NSE (broad universe)**
- Use `nselib.capital_market.bhav_copy_equities(trade_date)` to fetch the full daily universe.
- Filter to equity series `SctySrs == 'EQ'`.
- Expected universe size: ~2450+ symbols daily.

**BSE supplementation**
- Add **bselib** (Sachin-Kahandal/bselib) as a secondary data source.
- Practical usage targets (due to library reliability variability):
  - Bulk/block deals feed (BSE)
  - Corporate actions feed (BSE)
  - Potential quote/index supplementation when available
- Build fallback logic: if bselib fails/returns `{'info':'Error'}`, degrade gracefully.

**Deliverables**
- New `services/universe_service.py`:
  - `get_nse_universe(trade_date=None) -> List[Symbol]`
  - `get_bse_universe(trade_date=None) -> List[Symbol]` (best-effort)
  - `merge_universe(nse, bse)` with dedupe + mapping metadata

#### 6.1 Full-Market Scanner (multi-stage pipeline)
**Why multi-stage**: scanning 2450+ names with full indicator computation + 3 LLM calls each is infeasible.

**Stage A — Broad daily ingest (fast)**
- Pull bhav copy once per day (or per refresh window)
- Store as cached dataframe or in Mongo for reuse

**Stage B — Quant pre-filter (cheap, deterministic)**
Goal: reduce ~2450 → ~50–150 candidates.
- Liquidity filter:
  - min traded value / volume threshold from bhav (`TtlTrfVal`, `TtlTradgVol`)
- Momentum / setup filter:
  - strong close vs prev close
  - range expansion (true range proxy)
  - volume spike vs rolling median (if history cached)
- Optional fundamental screen (if available quickly):
  - avoid extreme leverage / missing financials

**Stage C — Deep feature computation (medium)**
Goal: reduce candidates → shortlist ~20–40.
- Fetch 3–6 months OHLCV only for candidates
- Compute expanded technicals via `full_technical_analysis`
- Fetch expanded fundamentals via `get_fundamentals`

**Stage D — God Mode LLM ensemble (expensive)**
Goal: produce **distilled BUY calls** for the shortlist.
- Run multi-LLM inference in parallel:
  - OpenAI (gpt-4.1)
  - Claude (sonnet)
  - Gemini (flash)
- Distill into consensus:
  - agreement score (0–1)
  - consensus action/timeframe/entry/stop/targets
  - dissent notes

**Stage E — Ranking + output formatting**
- Rank primarily by:
  - consensus action (BUY prioritized)
  - agreement score
  - confidence
  - risk/reward ratio
- Return only top N (default 10–20) BUY candidates.

**Deliverables**
- New `services/full_market_scanner.py`:
  - `prefilter_candidates(universe_df) -> candidates`
  - `build_shortlist(candidates) -> shortlist`
  - `god_mode_rank(shortlist) -> ranked results`

- New endpoint:
  - `POST /api/batch/god-scan`
    - body: `{ market: 'NSE'|'BSE'|'ALL', max_universe: int, shortlist: int, top_n: int, god_mode: true }`

#### 6.2 God Mode Intelligence Engine (inter-LLM bouncing)
**Additions to `services/intelligence_engine.py`**
- `generate_ai_signal_god_mode(symbol, raw_data, learning_context)`:
  1. call `generate_ai_signal(..., provider='openai')`
  2. call `generate_ai_signal(..., provider='claude')`
  3. call `generate_ai_signal(..., provider='gemini')`
  4. call `synthesize_consensus(signals=[a,b,c], raw_context)`

**Synthesis prompt contract**
- Input: 3 JSON signals + key raw metrics summary
- Output: a single canonical signal JSON +
  - `agreement_level`: HIGH/MEDIUM/LOW
  - `disagreements`: short bullets
  - `source_votes`: {openai: BUY, claude: HOLD, gemini: BUY}

**Batch ranking upgrade**
- Extend `generate_batch_ranking` to a God Mode variant:
  - each model produces rankings
  - synthesis merges into final ranking

#### 6.3 Frontend Updates (Scanner UX)
- Update BatchScanner into:
  - **Universe selector**: NSE / BSE / All
  - **Mode selector**: AI (single) vs **God Mode**
  - **Progress view**: Universe ingest → prefilter → shortlist → ensemble → distill
  - Results table additions:
    - agreement badge (HIGH/MED/LOW)
    - model votes (O/C/G)
    - distilled rationale

#### 6.4 Performance, Cost, and Reliability Guardrails
- Hard caps:
  - Universe scan max rows default 2450; UI allows sampling for dev
  - Shortlist max 40
  - Top N results 15
- Caching:
  - bhav copy cached daily
  - per-symbol OHLCV cached for scan window
- Failure isolation:
  - if one LLM fails, still synthesize using remaining models (2/3 quorum)

#### 6.5 Phase 6 Acceptance Criteria
- ✅ Scanner can ingest NSE full EQ universe from bhav copy and produce shortlist.
- ✅ God Mode returns distilled BUY calls with agreement score and votes.
- ✅ No explicit large-cap bias in universe selection.
- ✅ API latency acceptable with caps (shortlist + caching).
- ✅ Frontend communicates pipeline stages and displays consensus clearly.

---

## 3. Next Actions (immediate) (updated)
1. Start Phase 6 implementation:
   - Universe service (NSE bhav copy) + caching
   - God Mode consensus synthesis in intelligence engine
   - New `/api/batch/god-scan` endpoint
2. Update BatchScanner UI for Universe + God Mode + agreement visualization.

---

## 4. Success Criteria (updated)
- ✅ V1 remains functional (cockpit/analysis/scanner/chat).
- ✅ Phase 3: AI signals + history + evaluation + learning loop.
- ✅ Phase 4: Expanded technical/fundamental inputs + AI scanner ranking.
- ✅ Phase 5: Cockpit dashboard emphasizing liquidity/breadth/VIX/rotation/derivatives/events.
- 🟡 Phase 6:
  - Full-market scanning across **all NSE EQ** and best-effort **BSE supplementation**.
  - God Mode ensemble signals with consensus distillation + agreement transparency.
  - Scanner output optimized to surface **BUY calls** with risk controls.
- ✅ Compliance: explicit disclaimers, no guarantees, transparent assumptions, no fabricated numbers.

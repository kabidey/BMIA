import React, { useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import {
  Brain, Zap, Shield, BarChart3, TrendingUp, Target, Activity,
  Layers, Eye, Lock, Database, GitBranch, ChevronDown, ChevronRight,
  AlertTriangle, CheckCircle, Cpu, Crosshair, History, Sparkles,
  BookOpen, RefreshCw, PieChart
} from 'lucide-react';

function Section({ id, icon: Icon, iconColor, title, subtitle, children }) {
  return (
    <section id={id} className="scroll-mt-20">
      <div className="flex items-start gap-2 sm:gap-3 mb-3 sm:mb-4">
        <div className={`w-8 h-8 sm:w-9 sm:h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${iconColor || 'bg-[hsl(var(--primary))]/15'}`}>
          <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${iconColor?.includes('cyan') ? 'text-cyan-400' : iconColor?.includes('amber') ? 'text-amber-400' : iconColor?.includes('emerald') ? 'text-emerald-400' : iconColor?.includes('red') ? 'text-red-400' : 'text-[hsl(var(--primary))]'}`} />
        </div>
        <div>
          <h2 className="text-base sm:text-lg font-display font-bold text-[hsl(var(--foreground))]">{title}</h2>
          {subtitle && <p className="text-xs sm:text-sm text-[hsl(var(--muted-foreground))] mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="sm:ml-12 space-y-3 sm:space-y-4 text-sm text-[hsl(var(--foreground))]/85 leading-relaxed">
        {children}
      </div>
    </section>
  );
}

function Collapsible({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-[hsl(var(--border))] rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)} className="flex items-center justify-between w-full px-4 py-3 text-left text-sm font-medium text-[hsl(var(--foreground))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))]" style={{ transition: 'background 0.15s' }}>
        <span>{title}</span>
        {open ? <ChevronDown className="w-4 h-4 text-[hsl(var(--muted-foreground))]" /> : <ChevronRight className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />}
      </button>
      {open && <div className="px-4 py-3 text-sm text-[hsl(var(--foreground))]/80 leading-relaxed space-y-2 bg-[hsl(var(--card))]">{children}</div>}
    </div>
  );
}

function MetricBadge({ label, value, color }) {
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono border ${color || 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]'}`}>
      <span className="text-[hsl(var(--muted-foreground))]">{label}:</span>
      <span className="font-bold">{value}</span>
    </div>
  );
}

function PipelineStep({ step, title, desc, detail }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-[hsl(var(--primary))]/20 border border-[hsl(var(--primary))]/40 flex items-center justify-center text-xs font-bold text-[hsl(var(--primary))] font-mono">{step}</div>
        <div className="w-px flex-1 bg-[hsl(var(--border))] mt-1" />
      </div>
      <div className="pb-6">
        <p className="font-semibold text-[hsl(var(--foreground))]">{title}</p>
        <p className="text-[hsl(var(--muted-foreground))] text-xs mt-0.5">{desc}</p>
        {detail && <p className="text-[hsl(var(--foreground))]/70 text-xs mt-1 font-mono bg-[hsl(var(--surface-2))] px-2 py-1 rounded">{detail}</p>}
      </div>
    </div>
  );
}

const TOC_ITEMS = [
  { id: 'philosophy', label: 'Philosophy' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'market-cockpit', label: 'Market Cockpit' },
  { id: 'symbol-analysis', label: 'Symbol Analysis' },
  { id: 'god-mode', label: 'God Mode Scanner' },
  { id: 'signal-engine', label: 'Signal Engine' },
  { id: 'portfolio-engine', label: 'Portfolio Engine' },
  { id: 'hardening', label: 'Hardening Layer' },
  { id: 'daemon', label: 'Autonomous Daemon' },
  { id: 'backtest', label: '5-Year Backtest' },
  { id: 'simulation', label: 'Ensemble + Monte Carlo' },
  { id: 'walk-forward', label: 'Walk-Forward' },
  { id: 'custom-portfolios', label: 'Make Your Own' },
  { id: 'bse-guidance', label: 'BSE Guidance' },
  { id: 'anti-hallucination', label: 'Anti-Hallucination' },
  { id: 'security', label: 'OrgLens Auth' },
  { id: 'risk-framework', label: 'Risk Framework' },
];

export default function HowItWorks() {
  return (
    <div className="flex" data-testid="how-it-works-page">
      {/* Sticky TOC — large desktop only */}
      <nav className="hidden 2xl:block w-52 flex-shrink-0 sticky top-0 h-screen overflow-y-auto py-6 pr-4 border-r border-[hsl(var(--border))]">
        <p className="text-[10px] uppercase tracking-widest text-[hsl(var(--muted-foreground))] mb-3 px-3">On this page</p>
        {TOC_ITEMS.map(item => (
          <a key={item.id} href={`#${item.id}`} className="block px-3 py-1.5 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] rounded" style={{ transition: 'all 0.15s' }}>
            {item.label}
          </a>
        ))}
      </nav>

      {/* Main content */}
      <div className="flex-1 max-w-4xl mx-auto px-3 sm:px-6 py-4 sm:py-6 space-y-8 sm:space-y-10">
        {/* Hero */}
        <div className="relative overflow-hidden rounded-xl sm:rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4 sm:p-8" data-testid="how-hero">
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-[hsl(var(--primary))]/5 via-transparent to-cyan-500/3 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-mono uppercase tracking-widest bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] px-2 py-0.5 rounded">Documentation</span>
              <span className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">v3.0 — Hardened Pipeline</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-display font-bold tracking-tight text-[hsl(var(--foreground))]">
              How BMIA Works
            </h1>
            <p className="text-base text-[hsl(var(--muted-foreground))] mt-2 max-w-2xl leading-relaxed">
              Bharat Market Intel Agent is an autonomous, emotion-free quantitative analyst for Indian Equity and Commodity markets. It replaces the human-in-the-middle with code-enforced mathematical discipline, 3-model AI consensus, and real-time data pipelines covering 2,400+ NSE stocks.
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              <MetricBadge label="Stocks" value="2,400+" />
              <MetricBadge label="LLMs" value="3 (Consensus)" />
              <MetricBadge label="Strategies" value="6 AI + Custom" />
              <MetricBadge label="Capital" value="₹3 Cr" />
              <MetricBadge label="Guardrails" value="5 Code-Enforced" />
              <MetricBadge label="Ensemble" value="4 Models" />
              <MetricBadge label="MC Paths" value="10,000" />
              <MetricBadge label="Auth" value="OrgLens" />
            </div>
          </div>
        </div>

        {/* Philosophy */}
        <Section id="philosophy" icon={Brain} iconColor="bg-cyan-500/15" title="The Philosophy: Quant Has No Emotions" subtitle="Why machines must replace human judgment in portfolio construction">
          <p>
            Every retail investor and most fund managers share a fatal flaw: <strong>emotional decision-making</strong>. Fear during crashes leads to selling at bottoms. Greed during rallies leads to buying at tops. Anchoring bias makes traders hold losers. Confirmation bias makes them ignore red flags. Recency bias makes them chase yesterday's winners.
          </p>
          <p>
            BMIA eliminates this entirely. There is no human in the decision loop. The system operates on three principles:
          </p>
          <div className="grid grid-cols-1 gap-3">
            <Card className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
              <CardContent className="p-3">
                <Lock className="w-4 h-4 text-[hsl(var(--primary))] mb-1" />
                <p className="text-xs font-semibold">Code Over Conviction</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">Mathematical constraints (sector limits, position sizing, stop-losses) are enforced in Python, not via LLM prompts. The AI cannot override a 3-stock-per-sector limit no matter how "bullish" it feels.</p>
              </CardContent>
            </Card>
            <Card className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
              <CardContent className="p-3">
                <Eye className="w-4 h-4 text-cyan-400 mb-1" />
                <p className="text-xs font-semibold">Data Over Narrative</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">Every decision traces back to a number: RSI, P/E, ATR, volume ratio, OBV trend. If the data says "sell", the system sells — even if the media narrative is bullish. yfinance garbage (NaN, Inf, 500% dividend yields) is sanitized before any model sees it.</p>
              </CardContent>
            </Card>
            <Card className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
              <CardContent className="p-3">
                <GitBranch className="w-4 h-4 text-amber-400 mb-1" />
                <p className="text-xs font-semibold">Consensus Over Single-Point</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">No single AI model decides. GPT-4.1, Claude Sonnet, and Gemini Flash each independently analyze the same data. Only stocks that 2+ models agree on make the final portfolio. This eliminates single-model hallucination risk.</p>
              </CardContent>
            </Card>
          </div>
          <p>
            The result: a system that runs 24/7, processes 2,400+ stocks daily, enforces mathematical discipline on every position, and never panic-sells at 3 AM because of a scary headline.
          </p>
        </Section>

        {/* Architecture */}
        <Section id="architecture" icon={Layers} iconColor="bg-[hsl(var(--primary))]/15" title="System Architecture" subtitle="How the components connect">
          <div className="font-mono text-[10px] sm:text-xs bg-[hsl(var(--surface-2))] rounded-lg p-3 sm:p-4 border border-[hsl(var(--border))] overflow-x-auto whitespace-pre leading-5 text-[hsl(var(--foreground))]/80">{`
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (React + Tailwind + Recharts + Shadcn UI)            │
│  ┌──────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐ │
│  │Cockpit│ │ Analysis │ │ Scanner │ │ Signals  │ │ Analytics │ │
│  └──┬───┘ └────┬─────┘ └────┬────┘ └────┬─────┘ └─────┬─────┘ │
└─────┼──────────┼────────────┼───────────┼─────────────┼───────┘
      │          │            │           │             │
      ▼          ▼            ▼           ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI + 7 Route Modules + 2 Daemons)               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Routes: market, symbols, analysis, signals, guidance,   │   │
│  │         bse, portfolios                                 │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │                                       │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │ Services Layer                                          │   │
│  │  market_service    technical_service   fundamental_svc  │   │
│  │  intelligence_eng  portfolio_engine    portfolio_hard   │   │
│  │  portfolio_sim     signal_service      performance_svc  │   │
│  │  full_mkt_scanner  ai_agent_service    bse_price_svc   │   │
│  │  guidance_service  pdf_extractor       news_service     │   │
│  └─────────────┬──────────────┬────────────────────────────┘   │
│                │              │                                 │
│  ┌─────────────▼──┐  ┌───────▼──────────┐                     │
│  │ 3-LLM Ensemble │  │ Data Sources     │                     │
│  │ GPT-4.1        │  │ yfinance         │                     │
│  │ Claude Sonnet  │  │ NSE (nselib)     │                     │
│  │ Gemini Flash   │  │ BSE (bse lib)    │                     │
│  └────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   MongoDB        │
              │ portfolios       │
              │ signals          │
              │ backtests        │
              │ simulations      │
              │ scanner_history  │
              │ walk_forward     │
              └──────────────────┘`}</div>
        </Section>

        {/* Market Cockpit */}
        <Section id="market-cockpit" icon={Activity} iconColor="bg-emerald-500/15" title="Market Cockpit" subtitle="Real-time macro and micro diagnostics for the Indian market">
          <p>
            The Market Cockpit is the primary scan surface — designed for a trader to assess the entire Indian market regime in under 10 seconds. It aggregates data from NSE, BSE, and yfinance into a Bloomberg-inspired terminal layout.
          </p>
          <Collapsible title="What's displayed" defaultOpen>
            <p><strong>Indices Matrix:</strong> Nifty 50, Nifty Bank, Nifty IT, Nifty Pharma, Nifty Metal, Sensex — with LTP, % change, 1D range, and sparkline charts.</p>
            <p><strong>FII/DII Flows:</strong> Real-time institutional money flow (Foreign vs Domestic) — the single most important leading indicator for Indian markets.</p>
            <p><strong>Advance/Decline:</strong> Market breadth (how many stocks rising vs falling) to detect hidden divergences.</p>
            <p><strong>Sector Heatmap:</strong> Visual treemap of sector performance — instantly spot rotation from IT to Banks or Pharma to Metals.</p>
            <p><strong>Volume Shockers:</strong> Stocks with unusual volume (3x+ average) — signals institutional accumulation or distribution.</p>
            <p><strong>52-Week Highs/Lows:</strong> Momentum clusters and breakdown candidates.</p>
          </Collapsible>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Data refreshes automatically via background cache daemon. No manual polling needed.</p>
        </Section>

        {/* Symbol Analysis */}
        <Section id="symbol-analysis" icon={TrendingUp} iconColor="bg-[hsl(var(--primary))]/15" title="Symbol Analysis Engine" subtitle="25+ technical indicators, 30+ fundamental metrics, AI synthesis">
          <p>
            When you analyze a single stock, BMIA computes an exhaustive data packet. This is NOT a superficial "RSI + MACD" analysis. It's a full institutional-grade workup.
          </p>
          <Collapsible title="Technical Analysis (25+ indicators)" defaultOpen>
            <p className="font-mono text-[10px]">RSI (14) | MACD (12,26,9) + crossover | Bollinger Bands (20,2) + squeeze detection | ADX + DI+/DI- directional strength | Stochastic (14,3,3) | ATR (14) for volatility | OBV trend + divergence | Ichimoku Cloud (full 5 lines) | Moving Averages (10/20/50/100/200 SMA + EMA) | Golden Cross / Death Cross | Volume Structure Analysis (accumulation/distribution) | 52-Week High/Low + distance | Fibonacci retracement levels | Pivot Points (classic) | Breakout detection | Support/Resistance levels | Volume-Spread Analysis (VSA)</p>
          </Collapsible>
          <Collapsible title="Fundamental Analysis (30+ metrics)">
            <p className="font-mono text-[10px]">P/E | Forward P/E | PEG | P/B | P/S | EV/EBITDA | ROE | ROA | Profit Margin | Operating Margin | Gross Margin | Revenue Growth | Earnings Growth | Quarterly Earnings Trend | Debt/Equity | Current Ratio | Quick Ratio | FCF Yield | Dividend Yield | Payout Ratio | Beta | Insider Holdings % | Institutional Holdings % | Graham Intrinsic Value | Market Cap | Sector | Industry</p>
            <p className="mt-1">All values are <strong>sanitized</strong> by <code>validate_fundamentals()</code> — yfinance frequently returns garbage (500% dividend yields, NaN P/E ratios, negative market caps). BMIA caps, cleans, and flags every impossible value BEFORE any analysis.</p>
          </Collapsible>
          <Collapsible title="AI Synthesis">
            <p>After computing raw scores, the data is sent to an LLM for qualitative synthesis — connecting the dots between technicals and fundamentals in natural language. The AI explains <em>why</em> RSI=35 combined with ROE=22% and insider buying might be a setup, not just that the numbers exist.</p>
            <p>The Alpha Score (0-100) is a weighted composite: 40% Technical + 40% Fundamental + 20% Sentiment.</p>
          </Collapsible>
        </Section>

        {/* God Mode Scanner */}
        <Section id="god-mode" icon={Sparkles} iconColor="bg-violet-500/15" title="God Mode Scanner" subtitle="Full-market scan of 2,400+ NSE stocks through a 4-stage hardened pipeline">
          <p>
            The God Mode Scanner is the most computationally intensive feature. It scans every equity stock listed on NSE through a 4-stage pipeline that narrows 2,400+ stocks down to 10-15 distilled BUY calls with 3-LLM consensus.
          </p>
          <div className="space-y-0">
            <PipelineStep step="A" title="Universe Ingestion" desc="Load full NSE bhav copy (2,400+ EQ stocks)" detail="Source: nselib.capital_market.bhav_copy_equities() — cached daily" />
            <PipelineStep step="B" title="Quantitative Pre-Filter" desc="Score on momentum, range expansion, volume, price action → ~50 candidates" detail="Filters: traded_value > ₹50L, price > ₹10, composite score ranking" />
            <PipelineStep step="C" title="Deep Feature Computation" desc="Full technicals + fundamentals for top candidates → ~15 shortlist" detail="ThreadPoolExecutor (5 workers, 8s/stock timeout). Data sanitized via validate_fundamentals() + validate_technical(). Factor scores computed." />
            <PipelineStep step="D" title="God Mode 3-LLM Ensemble" desc="GPT-4.1, Claude Sonnet, Gemini Flash independently rank → consensus BUY calls" detail="120s hard timeout. Voting overlap: stocks picked by 2+ models rank higher. Each model provides AI score, action, conviction, rationale." />
          </div>
          <Card className="bg-amber-500/5 border-amber-500/20">
            <CardContent className="p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-[hsl(var(--foreground))]/80"><strong>Hardened:</strong> Build shortlist uses parallel fetching with per-stock timeouts to prevent yfinance hangs from stalling the entire scan. The LLM ensemble has a 120-second hard cap — if models don't respond, the system falls back to quantitative-only rankings.</p>
              </div>
            </CardContent>
          </Card>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">All completed scans are saved to Scanner History for comparison over time.</p>
        </Section>

        {/* Signal Engine */}
        <Section id="signal-engine" icon={Zap} iconColor="bg-emerald-500/15" title="AI Signal Engine" subtitle="Trade signal generation with code-enforced bounds and self-learning">
          <p>
            Signals are actionable trade recommendations with entry price, targets, stop-loss, and a confidence score. They can be generated for any stock via single-model or God Mode (3-LLM consensus).
          </p>
          <Collapsible title="Signal Generation Pipeline" defaultOpen>
            <p>1. Gather raw data: market snapshot, 25+ technicals, 30+ fundamentals, news headlines, sentiment analysis</p>
            <p>2. <strong>Sanitize inputs:</strong> <code>validate_fundamentals()</code> + <code>validate_technical()</code> clean yfinance garbage before the LLM sees it</p>
            <p>3. Inject learning context: past signal win rates, lessons learned, recent mistakes — so the AI improves over time</p>
            <p>4. LLM generates signal with entry, targets, stop-loss, key theses, invalidators</p>
            <p>5. <strong>Code-enforced validation</strong> (<code>_validate_signal_bounds()</code>):</p>
          </Collapsible>
          <Collapsible title="Code-Enforced Signal Guardrails">
            <div className="space-y-1 font-mono text-[10px]">
              <p>BUY target must be ABOVE entry → auto-fixed to entry*1.02 if violated</p>
              <p>SELL target must be BELOW entry → auto-fixed to entry*0.98 if violated</p>
              <p>BUY stop must be BELOW entry → auto-fixed to entry*0.95 if violated</p>
              <p>SELL stop must be ABOVE entry → auto-fixed to entry*1.05 if violated</p>
              <p>Target capped at ±30% from entry (no moonshot hallucinations)</p>
              <p>Stop-loss max 15% distance from entry</p>
              <p>Confidence clamped to 10-95 (LLMs love to say "95% confident")</p>
              <p>Horizon clamped to 1-90 days</p>
              <p>Risk/Reward ratio computed from VALIDATED (not raw) targets/stops</p>
              <p>Return calculations clamped to ±100% to reject garbage</p>
            </div>
          </Collapsible>
          <Collapsible title="Evaluation & Learning">
            <p>Open signals are evaluated against live market prices. When a signal hits its target, stop-loss, or expires, the outcome is recorded. The AI Learning module aggregates these outcomes into:</p>
            <p>- Win rate by action type (BUY vs SELL), sector, and confidence band</p>
            <p>- Lessons learned: patterns where the AI was wrong → fed back into future signal generation</p>
            <p>- Recent mistakes: explicit list of what went wrong → injected as "avoid this" context</p>
          </Collapsible>
        </Section>

        {/* Portfolio Engine */}
        <Section id="portfolio-engine" icon={Target} iconColor="bg-[hsl(var(--primary))]/15" title="Autonomous Portfolio Engine" subtitle="6 distinct strategies, ₹50L each, fully autonomous construction and rebalancing">
          <p>
            The crown jewel of BMIA. Six portfolios, each with ₹50 lakhs notional capital, each targeting a different market edge. No human touches the portfolio after construction — the daemon handles price updates, stop-loss enforcement, and rebalancing.
          </p>
          <div className="grid grid-cols-1 gap-3">
            {[
              { name: 'Bespoke Forward Looking', horizon: '6-12 months', desc: 'Future catalysts — capacity expansion, new orders, policy tailwinds. Growth + momentum weighted.' },
              { name: 'Quick Entry', horizon: '1-4 weeks', desc: 'Momentum breakouts — volume spikes, consolidation breakouts, RSI 50-70 sweet spot.' },
              { name: 'Long Term Compounder', horizon: '2-5 years', desc: 'Blue-chip moat businesses — consistent ROE >15%, low debt, market leaders.' },
              { name: 'Swing Trader', horizon: '1-2 weeks', desc: 'Mean reversion — RSI oversold (<30), Bollinger Band touches, technical bounce setups.' },
              { name: 'Alpha Generator', horizon: '3-6 months', desc: 'Contrarian plays — mispriced stocks, insider buying signals, value traps with catalysts.' },
              { name: 'Value Stocks', horizon: '1-3 years', desc: 'Deep value — low P/E, high dividend yield, P/B <1.5, Buffett-style margin of safety.' },
            ].map(s => (
              <Card key={s.name} className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
                <CardContent className="p-3">
                  <p className="text-xs font-semibold text-[hsl(var(--foreground))]">{s.name}</p>
                  <p className="text-[9px] text-[hsl(var(--primary))] font-mono mt-0.5">{s.horizon}</p>
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">{s.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <Collapsible title="Construction Pipeline (v3 Hardened)">
            <p>1. <strong>NSE Universe:</strong> 2,400+ EQ stocks from daily bhav copy</p>
            <p>2. <strong>Advanced Screener:</strong> Strategy-specific criteria (market cap, ROE, D/E, growth rates) → ~30-80 candidates</p>
            <p>3. <strong>Deep Enrichment:</strong> Full technicals + fundamentals + BSE filings for top 20 candidates</p>
            <p>4. <strong>BSE Guidance Integration:</strong> Real board meeting filings, insider trading data, credit ratings, corporate actions</p>
            <p>5. <strong>Hardened LLM Context:</strong> Anti-hallucination prompt with structured data tables, exact values, cross-validation rules</p>
            <p>6. <strong>God Mode 3-LLM Consensus:</strong> GPT-4.1 + Claude + Gemini independently select 10 stocks → voting overlap determines final picks</p>
            <p>7. <strong>Hardening Layers:</strong> Factor scoring → Sector enforcement (max 3) → Volatility-based sizing → Final allocation</p>
          </Collapsible>
        </Section>

        {/* Hardening */}
        <Section id="hardening" icon={Shield} iconColor="bg-red-500/15" title="The Hardening Layer" subtitle="Why LLMs cannot be trusted with math — and how code fixes it">
          <p>
            This is the most critical insight in BMIA's design: <strong>LLMs are excellent at qualitative synthesis but catastrophically bad at mathematical constraints.</strong> When asked to "allocate weights summing to 100% with max 3 per sector", GPT-4.1 routinely produces 105% total weight, 4 stocks from Financials, and P/E ratios it hallucinated.
          </p>
          <p>
            The solution: a dedicated <code>portfolio_hardening.py</code> module that runs AFTER the LLM output, overriding any violations with mathematically correct values.
          </p>
          <div className="space-y-3">
            {[
              { num: '1', title: 'Data Validation', desc: 'validate_fundamentals() + validate_technical() — sanitizes yfinance garbage. Dividend yield >20%? → null. P/E <0 or >500? → null. NaN, Inf? → null. RSI outside 0-100? → null. This runs BEFORE the LLM sees data.' },
              { num: '2', title: 'Quantitative Factor Scoring', desc: 'compute_factor_score() — Value (P/E, P/B, EV/EBITDA, FCF yield, dividend) + Quality (ROE, margins, D/E, current ratio, quarterly trend) + Growth (revenue, earnings, quarterly) + Momentum (RSI, MACD, ADX, breakout) + Volume (ratio, OBV, VSA). Weighted by strategy type.' },
              { num: '3', title: 'Sector Diversification', desc: 'enforce_sector_limits(max_per_sector=3) — Hard code. If the LLM picks 5 banks, the bottom 2 are removed and replaced with stocks from underrepresented sectors. Sorted by factor score.' },
              { num: '4', title: 'Volatility-Based Sizing', desc: 'volatility_based_weights() — Inverse ATR weighting. Less volatile stocks get higher weight (more stable portfolio). Clamped to 5-20% per stock. The LLM does NOT decide weights — code does.' },
              { num: '5', title: 'Stop-Loss Enforcement', desc: '8% hard stop-loss checked every rebalancing cycle. 20% auto-take-profit. These are programmatic — no LLM can override them. If a stock drops 8% from entry, it is REMOVED regardless of thesis.' },
            ].map(g => (
              <div key={g.num} className="flex gap-3 bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-[hsl(var(--border))]">
                <div className="w-6 h-6 rounded-full bg-red-500/15 border border-red-500/30 flex items-center justify-center text-[10px] font-bold text-red-400 font-mono flex-shrink-0">{g.num}</div>
                <div>
                  <p className="text-xs font-semibold text-[hsl(var(--foreground))]">{g.title}</p>
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{g.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Daemon */}
        <Section id="daemon" icon={RefreshCw} iconColor="bg-emerald-500/15" title="Autonomous Portfolio Daemon v3" subtitle="Self-healing background engine with DB kill switch">
          <p>
            The daemon is the nervous system of BMIA. It runs as a background thread inside the FastAPI process, waking every 5 minutes during market hours to perform three critical functions — without any human intervention.
          </p>
          <Collapsible title="Phase 1: Price Updates (9 AM - 4 PM IST)" defaultOpen>
            <p>Every 5-minute cycle, the daemon fetches live prices from yfinance for every holding in every active portfolio. It updates current_price, computes P&L percentage, and recalculates portfolio value. This is what keeps the "Current Value" number on your portfolio page alive.</p>
          </Collapsible>
          <Collapsible title="Phase 2: Stop-Loss & Take-Profit (9 AM - 4 PM IST)">
            <p><strong>8% Hard Stop:</strong> If any holding drops 8% or more from its entry price, the daemon removes it immediately. No human approval needed. No "let me wait for recovery." The stock is OUT. This is the single most important risk management mechanism in the system.</p>
            <p><strong>20% Take-Profit:</strong> If any holding rises 20%+ from entry, it's automatically exited. Winners are booked, not ridden into reversal. Every stop trigger is logged with timestamp and rationale in the rebalance history.</p>
          </Collapsible>
          <Collapsible title="Phase 3: Rebalance Evaluation (4 PM - 6 PM IST)">
            <p>After market close, the daemon evaluates whether each portfolio needs a strategic rebalance — not just stop-loss, but thesis-level changes. Should stock X be swapped for stock Y? Has the sector allocation drifted? This uses the same 3-LLM God Mode consensus pipeline as initial construction. Rate limited to max 1 rebalance per portfolio per day.</p>
          </Collapsible>
          <Collapsible title="Intelligence Features">
            <p><strong>Holiday Awareness:</strong> The daemon checks the NSE holiday calendar (stored in MongoDB). On Dr. Ambedkar Jayanti, Diwali, Republic Day — it skips all processing. No wasted yfinance calls on a closed market.</p>
            <p><strong>Weekend Detection:</strong> Saturday/Sunday → 30-minute sleep cycle instead of 5-minute.</p>
            <p><strong>DB Kill Switch:</strong> A toggle button in the Market Cockpit header lets you pause/resume the daemon instantly. The pause state is stored in MongoDB — survives server restarts. No code changes needed.</p>
            <p><strong>Sync pymongo:</strong> The v3 daemon uses synchronous pymongo instead of async motor. This eliminates the event loop lifecycle crashes ("cannot schedule new futures after shutdown") that plagued earlier versions.</p>
          </Collapsible>
        </Section>

        {/* Backtest */}
        <Section id="backtest" icon={History} iconColor="bg-[hsl(var(--primary))]/15" title="5-Year Backtest Engine" subtitle="Lookback analysis with Nifty 50 benchmark comparison">
          <p>
            Every portfolio is backtested against 5 years of historical data. This isn't a synthetic backtest with hindsight bias — it uses the actual stocks currently held and computes what their equal-weight portfolio would have returned over the past 60 months, compared to the Nifty 50 benchmark.
          </p>
          <Collapsible title="Metrics Computed" defaultOpen>
            <p><strong>CAGR:</strong> Compound Annual Growth Rate — the annualized return over 5 years</p>
            <p><strong>Alpha:</strong> CAGR minus Nifty 50 CAGR — the excess return above the benchmark</p>
            <p><strong>Sharpe Ratio:</strong> Risk-adjusted return (risk-free rate = 6% for India). Sharpe &gt; 1 = good, &gt; 2 = excellent</p>
            <p><strong>Max Drawdown:</strong> Worst peak-to-trough decline — measures tail risk</p>
            <p><strong>Win Rate:</strong> Percentage of months with positive returns</p>
            <p><strong>Annual Volatility:</strong> Standard deviation of returns, annualized</p>
          </Collapsible>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Results cached for 24 hours in MongoDB. Recomputed when portfolio holdings change.</p>
        </Section>

        {/* Simulation */}
        <Section id="simulation" icon={Cpu} iconColor="bg-cyan-500/15" title="4-Model Ensemble + Monte Carlo" subtitle="Multi-model neural ensemble calibrated 10,000-path forward projection">
          <p>
            The forward simulation engine combines four independent forecasting models with classical quantitative finance. Each model sees the same 5 years of daily portfolio returns but learns different patterns. Their predictions are weighted by validation accuracy — the model that's been most right gets the most influence.
          </p>
          <Collapsible title="Model 1: LSTM (Sequential Momentum)" defaultOpen>
            <p><strong>Architecture:</strong> 2-layer LSTM, hidden_size=128, dropout=0.3, probabilistic output (mu, log_sigma)</p>
            <p><strong>Captures:</strong> Sequential momentum, trend persistence, short-term mean reversion. LSTMs excel at remembering patterns across 20-60 day windows — capturing how stocks that rallied last week tend to behave this week.</p>
            <p><strong>Training:</strong> AdamW optimizer with weight decay (1e-4), CosineAnnealing LR scheduler, 120 epochs max, early stopping (patience=20). Gaussian NLL loss.</p>
          </Collapsible>
          <Collapsible title="Model 2: Attention-LSTM (Long-Range Dependencies)">
            <p><strong>Architecture:</strong> 2-layer LSTM + Self-Attention layer + LayerNorm residual, hidden_size=128</p>
            <p><strong>Captures:</strong> Long-range dependencies that vanilla LSTM misses — quarterly earnings cycles (90-day patterns), seasonal effects (budget season, monsoon impact on agri stocks), annual rebalancing flows. The attention mechanism can directly connect a return from 200 days ago to today's prediction.</p>
            <p><strong>Attention mechanism:</strong> Query-Key-Value self-attention over the full LSTM hidden sequence, scaled by sqrt(hidden_dim). No masking — full bidirectional attention over the lookback window.</p>
          </Collapsible>
          <Collapsible title="Model 3: GRU (Different Gradient Dynamics)">
            <p><strong>Architecture:</strong> 2-layer GRU, hidden_size=96, dropout=0.3</p>
            <p><strong>Captures:</strong> GRU has a simpler gate structure than LSTM (2 gates vs 3). This means different gradient flow characteristics — it sometimes captures fast regime changes that LSTM's forget gate smooths over. Having both in the ensemble means we get the best of both gradient dynamics.</p>
            <p><strong>Why smaller?</strong> GRU is more parameter-efficient. 96 hidden units in GRU ≈ 128 in LSTM in terms of effective capacity.</p>
          </Collapsible>
          <Collapsible title="Model 4: GARCH(1,1) (Volatility Specialist)">
            <p><strong>Model:</strong> sigma²(t) = omega + alpha*r²(t-1) + beta*sigma²(t-1), with alpha=0.06, beta=0.93</p>
            <p><strong>Captures:</strong> Volatility clustering — the empirical fact that large moves tend to follow large moves. GARCH is the industry standard at every major quant desk for volatility forecasting. It has no opinion about direction (mean), only about how much the market will move.</p>
            <p><strong>Variance targeting:</strong> omega is calibrated from the unconditional variance of the full sample. This ensures long-run mean reversion in volatility.</p>
          </Collapsible>
          <Collapsible title="Ensemble Weighting">
            <p><strong>Split:</strong> 80% training / 20% validation on the chronological return series (no shuffling — respects time order)</p>
            <p><strong>Weighting:</strong> Inverse validation loss. If LSTM had val_loss=0.5, Attention-LSTM had 0.3, GRU had 0.6, and GARCH had 1.0 — Attention-LSTM gets the highest weight because it predicted the validation set best.</p>
            <p><strong>Adaptive:</strong> On random/noisy data, GARCH dominates (neural nets can't learn random). On trending markets, LSTM/Attention-LSTM dominate. The weights adapt automatically to the current market regime.</p>
          </Collapsible>
          <Collapsible title="Monte Carlo (Geometric Brownian Motion)">
            <p><strong>Model:</strong> S(t+1) = S(t) * exp((mu - sigma²/2)*dt + sigma*sqrt(dt)*Z) where Z ~ N(0,1)</p>
            <p><strong>Calibration:</strong> mu and sigma come from the ensemble-weighted forecast, not raw historical data</p>
            <p><strong>Paths:</strong> 10,000 independent simulations over 252 trading days (1 year)</p>
            <p><strong>Seed:</strong> Fixed (42) for reproducibility across runs</p>
            <p><strong>Fan Chart:</strong> Weekly percentile bands (5th, 25th, 50th, 75th, 95th) for visual confidence intervals</p>
            <p><strong>Distribution:</strong> Terminal return histogram across all 10,000 paths</p>
          </Collapsible>
          <Collapsible title="Risk Metrics Computed">
            <p><strong>VaR (95%, 99%):</strong> Value at Risk — maximum loss at given confidence level over 1 year</p>
            <p><strong>CVaR / Expected Shortfall:</strong> Average loss in the worst 5% of scenarios — captures tail risk better than VaR</p>
            <p><strong>Probability of Profit:</strong> % of 10,000 paths that end above starting value</p>
            <p><strong>Max Expected Drawdown:</strong> Average worst peak-to-trough across 1,000 sampled paths</p>
            <p><strong>Return Range (25-75th):</strong> The "likely" range of outcomes</p>
            <p><strong>Terminal Stats:</strong> Worst case, best case, median, mean portfolio values</p>
          </Collapsible>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Computed in background threads. Cached for 12 hours. Requires 2 vCPU / 8GB RAM.</p>
        </Section>

        {/* Walk-Forward */}
        <Section id="walk-forward" icon={Crosshair} iconColor="bg-amber-500/15" title="Walk-Forward Tracking" subtitle="Does the simulation actually predict reality?">
          <p>
            A backtest tells you what would have happened. A simulation tells you what might happen. Walk-forward tracking tells you <strong>whether the simulation was right</strong>.
          </p>
          <p>
            At regular intervals, BMIA snapshots: (1) the Monte Carlo forecast (expected return, VaR, probability of profit) and (2) the actual portfolio performance at that moment. Over time, this builds a Forecast vs Actual dataset that measures the simulation engine's calibration.
          </p>
          <p>
            A well-calibrated simulation should have: actual returns falling within the 25th-75th percentile band ~50% of the time, and within the 5th-95th band ~90% of the time. If the simulation consistently over-predicts, the LSTM parameters need recalibration.
          </p>
        </Section>

        {/* Custom Portfolios */}
        <Section id="custom-portfolios" icon={Target} iconColor="bg-[hsl(var(--primary))]/15" title="Make Your Own Portfolio" subtitle="Compete against the AI — build, rebalance, and track your own picks">
          <p>
            BMIA doesn't just tell you what to buy — it lets you prove your own thesis. Create up to 5 custom portfolios with up to 10 stocks each, allocate weights, and track performance with the same analytical rigor as the AI portfolios.
          </p>
          <Collapsible title="Creation Flow" defaultOpen>
            <p>1. <strong>Name it:</strong> "My Growth Picks", "Dividend Kings", "Momentum Play" — whatever your thesis</p>
            <p>2. <strong>Search & add stocks:</strong> Autocomplete search across 2,400+ NSE stocks. Add up to 10.</p>
            <p>3. <strong>Set weights:</strong> Manual +/- buttons per stock, or auto-balance for equal weight. Weights normalize to 100%.</p>
            <p>4. <strong>Save:</strong> The system fetches live prices, computes quantities from ₹50L notional capital, and creates the portfolio.</p>
          </Collapsible>
          <Collapsible title="Manual Rebalancing">
            <p>Hit "Rebalance" on any custom portfolio to enter rebalance mode. You can:</p>
            <p>- <strong>Add new stocks</strong> via the search bar</p>
            <p>- <strong>Remove existing stocks</strong> with one click</p>
            <p>- <strong>Adjust weights</strong> up or down</p>
            <p>Every rebalance is logged with a timestamped snapshot: what was added, removed, and weight-changed. Full audit trail.</p>
          </Collapsible>
          <Collapsible title="Full Analytics">
            <p>Custom portfolios get the same analytical treatment as AI portfolios:</p>
            <p>- <strong>5-Year Backtest</strong> vs Nifty 50 (CAGR, Alpha, Sharpe, Max Drawdown)</p>
            <p>- <strong>4-Model Ensemble + Monte Carlo</strong> forward simulation (fan chart, VaR, CVaR, P(Profit))</p>
            <p>- <strong>Sector allocation pie chart</strong></p>
            <p>- <strong>Holdings table</strong> with live P&L, signal badges</p>
            <p>This means you can directly compare your picks against the AI's picks — same metrics, same benchmarks, no excuses.</p>
          </Collapsible>
          <Card className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
            <CardContent className="p-3">
              <p className="text-xs font-semibold text-[hsl(var(--foreground))] mb-2">The Portfolio Construction Playbook</p>
              <div className="space-y-1 text-[10px] text-[hsl(var(--muted-foreground))]">
                <p>1. Diversify across sectors — max 30% in any single sector</p>
                <p>2. Size by conviction — higher weight = higher conviction, cap at 20%</p>
                <p>3. Mix time horizons — compounders + momentum</p>
                <p>4. Mind liquidity — daily volume &gt; ₹5 Cr</p>
                <p>5. Set a stop-loss mentally — 8-10% is professional</p>
                <p>6. Rebalance quarterly — trim winners, cut losers</p>
                <p>7. Track against Nifty 50 — if you can't beat the index, buy the index</p>
              </div>
            </CardContent>
          </Card>
        </Section>

        {/* BSE Guidance */}
        <Section id="bse-guidance" icon={BookOpen} iconColor="bg-[hsl(var(--primary))]/15" title="BSE Guidance & PDF Intelligence" subtitle="Inline extraction of corporate filings for real informational edge">
          <p>
            Most retail tools show you price charts. BMIA reads BSE corporate filings — the same documents that institutional investors and FIIs use to make decisions.
          </p>
          <Collapsible title="What's extracted" defaultOpen>
            <p><strong>Board Meeting Outcomes:</strong> Dividend declarations, stock splits, bonus issues, rights issues</p>
            <p><strong>Insider Trading:</strong> Promoter buying (bullish signal) or selling (bearish signal) with exact quantities and prices</p>
            <p><strong>Credit Ratings:</strong> Upgrades and downgrades from CRISIL, ICRA, CARE, India Ratings</p>
            <p><strong>Corporate Actions:</strong> Mergers, demergers, name changes, face value changes</p>
            <p><strong>Quarterly Results:</strong> Revenue, net profit, EPS trends extracted from result PDFs</p>
          </Collapsible>
          <p>
            A background daemon scrapes BSE filings daily, extracts text from PDFs using pdfplumber, chunks the content, and stores it in MongoDB. When a stock is being analyzed for portfolio construction, the relevant guidance chunks are injected directly into the LLM context — giving the AI information that most retail traders never see.
          </p>
        </Section>

        {/* Anti-Hallucination */}
        <Section id="anti-hallucination" icon={AlertTriangle} iconColor="bg-red-500/15" title="Anti-Hallucination Protocol" subtitle="How BMIA prevents LLMs from making things up">
          <p>
            LLMs hallucinate. This is not a bug — it's a fundamental property of next-token prediction. When an LLM doesn't know a stock's P/E ratio, it invents one that "sounds right". When asked for 10 stocks, it might give you 9 or 11. When asked for weights summing to 100%, it gives 103%.
          </p>
          <p>BMIA's anti-hallucination strategy operates at 4 levels:</p>
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs"><strong>Level 1 — Data Sanitization:</strong> All yfinance/NSE/BSE data is cleaned by validate_fundamentals() and validate_technical() BEFORE the LLM sees it. Impossible values (NaN, Inf, 500% yields) are nulled. This removes the temptation for the LLM to use garbage data.</p>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs"><strong>Level 2 — Structured Prompts:</strong> Data is formatted as exact tables with specific values. The prompt explicitly states: "You MUST ONLY reference data points that appear in the provided context. If a metric says N/A, do NOT invent a value." Cross-validation is required: if technicals say BUY but fundamentals are deteriorating, the LLM must FLAG THE CONFLICT.</p>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs"><strong>Level 3 — Multi-Model Consensus:</strong> 3 independent LLMs analyze the same data. A stock must be picked by 2+ models to make the consensus list. This eliminates single-model hallucination — if GPT invents a stock that doesn't exist, Claude and Gemini won't pick it.</p>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs"><strong>Level 4 — Code Override:</strong> portfolio_hardening.py runs AFTER LLM output and enforces mathematical correctness. Weights are recalculated by code. Sector limits are enforced by code. Factor scores are computed by code. The LLM's job is ONLY qualitative narrative — all quantitative decisions are made in Python.</p>
            </div>
          </div>
        </Section>

        {/* Security */}
        <Section id="security" icon={Lock} iconColor="bg-red-500/15" title="OrgLens Authentication" subtitle="Employee verification + local password auth with JWT sessions">
          <p>
            BMIA access is restricted to verified SMIFS employees. Authentication uses a two-step process: OrgLens employee verification followed by local password authentication.
          </p>
          <Collapsible title="How it works" defaultOpen>
            <p><strong>Step 1 — Email Verification:</strong> User enters their SMIFS email. The backend calls the OrgLens Employee Stack API to verify: Is this a real, active employee? The API returns name, department, designation, and employment status.</p>
            <p><strong>Step 2a — New User:</strong> If no password exists, the user is prompted to create one. Password is bcrypt-hashed (salt round 12) and stored in MongoDB. Never in plaintext.</p>
            <p><strong>Step 2b — Returning User:</strong> If a password already exists, they enter it. bcrypt.checkpw verifies against the stored hash.</p>
            <p><strong>Session:</strong> Successful login issues a JWT token. Regular employees get 1-hour sessions with auto-logout (frontend checks every 30 seconds). The superadmin gets a 365-day persistent session.</p>
          </Collapsible>
          <Collapsible title="OrgLens Integration">
            <p>The OrgLens API at orglens.pesmifs.com provides real-time employee data. Every login attempt verifies the employee's current status — if someone leaves SMIFS, their access is automatically revoked on next login attempt even if their password is still valid.</p>
            <p>API call: <code>GET /api/v1/employee/by-email/name@smifs.com</code> with X-API-Key header.</p>
            <p>Returns: name, department, designation, employment_status. Only "Active" status grants access.</p>
          </Collapsible>
          <Collapsible title="Security Properties">
            <p><strong>No credential leakage:</strong> Passwords are bcrypt-hashed, never stored in plaintext. OrgLens API key is in environment variables, never in code.</p>
            <p><strong>Auto-revocation:</strong> Every login re-checks OrgLens. Terminated employees are immediately locked out.</p>
            <p><strong>JWT auto-expiry:</strong> 1-hour tokens for regular users. Frontend force-logouts on expiry. No stale sessions.</p>
            <p><strong>Superadmin:</strong> somnath.dey@smifs.com — 365-day session for operational continuity.</p>
          </Collapsible>
        </Section>

        {/* Risk Framework */}
        <Section id="risk-framework" icon={Shield} iconColor="bg-amber-500/15" title="Risk Management Framework" subtitle="Multi-layered defense against drawdowns">
          <p>
            Risk management is not a feature — it's the foundation. Every layer of BMIA has built-in risk controls.
          </p>
          <div className="overflow-x-auto -mx-3 px-3">
            <table className="w-full text-xs border border-[hsl(var(--border))] rounded-lg overflow-hidden min-w-[500px]">
              <thead>
                <tr className="bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]">
                  <th className="px-3 py-2 text-left">Layer</th>
                  <th className="px-3 py-2 text-left">Mechanism</th>
                  <th className="px-3 py-2 text-left">Enforcement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))]">
                {[
                  ['Position Sizing', 'Inverse ATR volatility weighting, 5-20% per stock', 'Code (portfolio_hardening.py)'],
                  ['Sector Diversification', 'Max 3 stocks per sector', 'Code (enforce_sector_limits)'],
                  ['Stop-Loss', '8% hard stop from entry price', 'Code (evaluate_rebalancing)'],
                  ['Take-Profit', '20% auto-exit', 'Code (evaluate_rebalancing)'],
                  ['Signal Validation', 'Target/stop bounds, ±30% target cap, 15% stop max', 'Code (_validate_signal_bounds)'],
                  ['Data Sanitization', 'NaN/Inf removal, value capping, garbage detection', 'Code (validate_fundamentals)'],
                  ['LLM Consensus', '2+ model agreement required for stock selection', 'Architecture (God Mode)'],
                  ['Ensemble Clamping', '±50% annualized cap on ensemble-predicted returns', 'Code (train_ensemble)'],
                  ['Daemon Kill Switch', 'DB-driven pause/resume, holiday/weekend awareness', 'UI toggle + MongoDB'],
                  ['Backtest Evidence', '5-year lookback required before live deployment', 'Workflow'],
                  ['Walk-Forward', 'Forecast vs actual tracking for simulation calibration', 'Monitoring'],
                ].map(([layer, mech, enf]) => (
                  <tr key={layer} className="text-[hsl(var(--foreground))]/80">
                    <td className="px-3 py-2 font-medium">{layer}</td>
                    <td className="px-3 py-2">{mech}</td>
                    <td className="px-3 py-2 font-mono text-[10px]">{enf}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* Disclaimer */}
        <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4 mt-8" data-testid="sebi-disclaimer-how">
          <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
            <strong>SEBI Disclaimer:</strong> BMIA is a research and educational tool. It does not constitute investment advice, nor is it a recommendation to buy, sell, or hold any security. Past performance (backtest results) does not guarantee future returns. Forward simulations are probabilistic estimates, not predictions. All AI-generated analysis is for informational purposes only. Always conduct your own due diligence and consult a SEBI-registered financial advisor before making investment decisions.
          </p>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Briefcase, Send, Loader2, Sparkles, CheckCircle2, AlertCircle,
  TrendingUp, TrendingDown, Minus, Scale as ScaleIcon, Brain,
  LineChart as LineChartIcon, MessagesSquare, Newspaper, Activity,
  Shield, Target, Clock, RefreshCw, Play, Pause, Cpu, History,
} from 'lucide-react';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Pipeline stages — must match backend `_patch(stage,...)` ordering
const STAGES = [
  { key: 'data_gathering', label: 'Data Gathering', icon: Activity,        group: 'data' },
  { key: 'analysts',       label: 'Analysts',       icon: Brain,           group: 'analyst' },
  { key: 'debate',         label: 'Bull / Bear',    icon: MessagesSquare,  group: 'debate' },
  { key: 'trader',         label: 'Trader',         icon: TrendingUp,      group: 'trader' },
  { key: 'risk',           label: 'Risk Manager',   icon: Shield,          group: 'risk' },
  { key: 'fund_manager',   label: 'Fund Manager',   icon: Briefcase,       group: 'final' },
];

const VERDICT_COLOR = {
  STRONG_BUY:  'text-emerald-300 bg-emerald-500/15 border-emerald-500/40',
  BUY:         'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  HOLD:        'text-amber-300 bg-amber-500/10 border-amber-500/30',
  SELL:        'text-red-300 bg-red-500/10 border-red-500/30',
  STRONG_SELL: 'text-red-300 bg-red-500/15 border-red-500/40',
  BULLISH:     'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  BEARISH:     'text-red-300 bg-red-500/10 border-red-500/30',
  NEUTRAL:     'text-[hsl(var(--muted-foreground))] bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]',
  POSITIVE:    'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  NEGATIVE:    'text-red-300 bg-red-500/10 border-red-500/30',
  RISK_ON:     'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  RISK_OFF:    'text-red-300 bg-red-500/10 border-red-500/30',
  GOOD:        'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  POOR:        'text-red-300 bg-red-500/10 border-red-500/30',
  LOW:         'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  MEDIUM:      'text-amber-300 bg-amber-500/10 border-amber-500/30',
  HIGH:        'text-red-300 bg-red-500/10 border-red-500/30',
};

const verdictPill = (v) => VERDICT_COLOR[v] || VERDICT_COLOR.NEUTRAL;

const StageDot = ({ status }) => {
  if (status === 'done') return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
  if (status === 'running') return <Loader2 className="w-3.5 h-3.5 text-[hsl(var(--primary))] animate-spin" />;
  if (status === 'error') return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
  return <Minus className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />;
};

const VerdictBadge = ({ value }) => value ? (
  <span className={`text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${verdictPill(value)}`}>
    {value}
  </span>
) : null;

const ConfBar = ({ value }) => {
  const pct = Math.max(0, Math.min(1, Number(value) || 0)) * 100;
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1 bg-[hsl(var(--surface-2))] rounded-full overflow-hidden">
        <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">{pct.toFixed(0)}%</span>
    </div>
  );
};

// ── Individual stage card renderers ───────────────────────────────────────
const AnalystCard = ({ title, icon: Icon, data }) => {
  if (!data) return null;
  const verdict = data.verdict;
  const rationale = data.rationale || data._warning || data.error;
  const strengths = data.key_strengths || data.catalysts || data.key_signals || [];
  const weaknesses = data.key_weaknesses || data.risks || [];
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3" data-testid={`analyst-card-${title.toLowerCase()}`}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5 text-xs font-medium text-[hsl(var(--foreground))]">
          <Icon className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
          {title}
        </div>
        <VerdictBadge value={verdict} />
      </div>
      {data.confidence !== undefined && <ConfBar value={data.confidence} />}
      {(data.support || data.resistance) && (
        <div className="flex gap-3 text-[10px] font-mono text-[hsl(var(--muted-foreground))] mt-1.5">
          {data.support && <span>S: <span className="text-emerald-400">{data.support}</span></span>}
          {data.resistance && <span>R: <span className="text-red-400">{data.resistance}</span></span>}
          {data.trend && <span className="capitalize">trend: {data.trend}</span>}
        </div>
      )}
      {rationale && (
        <p className="text-[11px] text-[hsl(var(--muted-foreground))] mt-2 leading-relaxed line-clamp-6">
          {rationale}
        </p>
      )}
      {strengths.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {strengths.slice(0, 3).map((s, i) => (
            <li key={i} className="text-[10px] text-emerald-400/90 flex gap-1"><span>+</span><span>{s}</span></li>
          ))}
        </ul>
      )}
      {weaknesses.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {weaknesses.slice(0, 3).map((s, i) => (
            <li key={i} className="text-[10px] text-red-400/90 flex gap-1"><span>−</span><span>{s}</span></li>
          ))}
        </ul>
      )}
    </div>
  );
};

const DebateCard = ({ side, data }) => {
  if (!data) return null;
  const isBull = side === 'Bull';
  return (
    <div className={`rounded-lg border p-3 ${isBull ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}
         data-testid={`debate-card-${side.toLowerCase()}`}>
      <div className="flex items-center justify-between mb-1.5">
        <div className={`flex items-center gap-1.5 text-xs font-medium ${isBull ? 'text-emerald-300' : 'text-red-300'}`}>
          {isBull ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
          {side} Researcher
        </div>
        {data.conviction !== undefined && (
          <span className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">
            conv {Math.round(data.conviction * 100)}%
          </span>
        )}
      </div>
      {data.conviction !== undefined && <ConfBar value={data.conviction} />}
      {data.thesis && <p className="text-[11px] text-[hsl(var(--muted-foreground))] mt-2 leading-relaxed line-clamp-7">{data.thesis}</p>}
      {(data.key_drivers || data.key_risks) && (
        <ul className="mt-2 space-y-0.5">
          {(data.key_drivers || data.key_risks).slice(0, 4).map((s, i) => (
            <li key={i} className={`text-[10px] flex gap-1 ${isBull ? 'text-emerald-400/90' : 'text-red-400/90'}`}>
              <span>•</span><span>{s}</span>
            </li>
          ))}
        </ul>
      )}
      {data.target_horizon_months && (
        <div className="text-[10px] font-mono text-[hsl(var(--muted-foreground))] mt-1.5 flex items-center gap-1">
          <Clock className="w-3 h-3" /> {data.target_horizon_months}m horizon
        </div>
      )}
    </div>
  );
};

const TraderCard = ({ data }) => {
  if (!data) return null;
  return (
    <Card className="p-3 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]" data-testid="trader-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-medium">
          <TrendingUp className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
          Trader Proposal
        </div>
        <VerdictBadge value={data.action} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
        <div><div className="text-[hsl(var(--muted-foreground))]">Entry</div><div className="text-[hsl(var(--foreground))]">{data.entry_price ?? '-'}</div></div>
        <div><div className="text-[hsl(var(--muted-foreground))]">Stop</div><div className="text-red-400">{data.stop_loss ?? '-'}</div></div>
        <div><div className="text-[hsl(var(--muted-foreground))]">Target</div><div className="text-emerald-400">{data.target_price ?? '-'}</div></div>
        <div><div className="text-[hsl(var(--muted-foreground))]">Horizon</div><div>{data.horizon_months ?? '-'}m</div></div>
        <div><div className="text-[hsl(var(--muted-foreground))]">Position</div><div>{data.position_size_pct_of_portfolio ?? '-'}%</div></div>
        <div><div className="text-[hsl(var(--muted-foreground))]">Conv</div><div>{data.conviction ? Math.round(data.conviction * 100) + '%' : '-'}</div></div>
      </div>
      {data.rationale && <p className="text-[11px] text-[hsl(var(--muted-foreground))] mt-2 leading-relaxed">{data.rationale}</p>}
    </Card>
  );
};

const RiskCard = ({ data }) => {
  if (!data) return null;
  return (
    <Card className="p-3 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]" data-testid="risk-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-medium">
          <Shield className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
          Risk Manager
        </div>
        <span className={`text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${
          data.approve ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30'
                       : 'text-red-300 bg-red-500/10 border-red-500/30'
        }`}>
          {data.approve ? 'APPROVED' : 'BLOCKED'}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div>
          <div className="text-[hsl(var(--muted-foreground))]">Concentration</div>
          <VerdictBadge value={data.concentration_risk} />
        </div>
        <div>
          <div className="text-[hsl(var(--muted-foreground))]">Regulatory</div>
          <VerdictBadge value={data.regulatory_risk} />
        </div>
        <div>
          <div className="text-[hsl(var(--muted-foreground))]">Regime fit</div>
          <VerdictBadge value={data.market_regime_fit} />
        </div>
      </div>
      {data.max_position_size_pct !== undefined && (
        <div className="text-[10px] font-mono text-[hsl(var(--muted-foreground))] mt-2">
          Max position: <span className="text-[hsl(var(--foreground))]">{data.max_position_size_pct}%</span>
        </div>
      )}
      {data.concerns?.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {data.concerns.slice(0, 4).map((c, i) => (
            <li key={i} className="text-[10px] text-amber-400/90 flex gap-1"><span>!</span><span>{c}</span></li>
          ))}
        </ul>
      )}
      {data.rationale && <p className="text-[11px] text-[hsl(var(--muted-foreground))] mt-2 leading-relaxed">{data.rationale}</p>}
    </Card>
  );
};

const FundManagerCard = ({ data, symbol }) => {
  if (!data) return null;
  return (
    <Card className="p-4 bg-gradient-to-br from-[hsl(var(--surface-1))] to-[hsl(var(--surface-2))] border-[hsl(var(--primary))]/40 ring-1 ring-[hsl(var(--primary))]/20"
          data-testid="fund-manager-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider">
          <Briefcase className="w-4 h-4 text-[hsl(var(--primary))]" />
          Fund Manager Verdict — {symbol}
        </div>
        <VerdictBadge value={data.final_verdict} />
      </div>
      {data.headline && (
        <h2 className="text-base font-display text-[hsl(var(--foreground))] my-2 leading-snug">
          {data.headline}
        </h2>
      )}
      {data.confidence !== undefined && <ConfBar value={data.confidence} />}
      {data.approved_action && (
        <div className="grid grid-cols-3 gap-2 text-[10px] font-mono mt-3 p-2 bg-[hsl(var(--surface-2))] rounded">
          <div><div className="text-[hsl(var(--muted-foreground))]">Action</div><div className="text-[hsl(var(--foreground))]">{data.approved_action.action}</div></div>
          <div><div className="text-[hsl(var(--muted-foreground))]">Entry</div><div>{data.approved_action.entry_price ?? '-'}</div></div>
          <div><div className="text-[hsl(var(--muted-foreground))]">Stop</div><div className="text-red-400">{data.approved_action.stop_loss ?? '-'}</div></div>
          <div><div className="text-[hsl(var(--muted-foreground))]">Target</div><div className="text-emerald-400">{data.approved_action.target_price ?? '-'}</div></div>
          <div><div className="text-[hsl(var(--muted-foreground))]">Horizon</div><div>{data.approved_action.horizon_months ?? '-'}m</div></div>
          <div><div className="text-[hsl(var(--muted-foreground))]">Size</div><div>{data.approved_action.max_position_size_pct ?? '-'}%</div></div>
        </div>
      )}
      {data.key_reasons?.length > 0 && (
        <div className="mt-3">
          <div className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-1">Key reasons</div>
          <ul className="space-y-0.5">
            {data.key_reasons.slice(0, 5).map((r, i) => (
              <li key={i} className="text-[11px] text-[hsl(var(--foreground))] flex gap-1.5"><Target className="w-3 h-3 mt-0.5 text-[hsl(var(--primary))] shrink-0" /><span>{r}</span></li>
            ))}
          </ul>
        </div>
      )}
      {data.watch_outs?.length > 0 && (
        <div className="mt-2">
          <div className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-1">Watch-outs</div>
          <ul className="space-y-0.5">
            {data.watch_outs.slice(0, 4).map((r, i) => (
              <li key={i} className="text-[11px] text-amber-400/90 flex gap-1.5"><AlertCircle className="w-3 h-3 mt-0.5 shrink-0" /><span>{r}</span></li>
            ))}
          </ul>
        </div>
      )}
      {data.rationale && (
        <p className="text-[11px] text-[hsl(var(--muted-foreground))] mt-3 leading-relaxed">{data.rationale}</p>
      )}
    </Card>
  );
};

// ── Daemon panel: live NIFTY-500 churn + decisions feed ──────────────────
const DaemonPanel = () => {
  const [status, setStatus] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [counts, setCounts] = useState({});
  const [filter, setFilter] = useState('all');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, d] = await Promise.all([
        fetch(`${BACKEND_URL}/api/funds/daemon/status`).then(r => r.ok ? r.json() : null),
        fetch(`${BACKEND_URL}/api/funds/decisions?source=daemon&limit=30${filter !== 'all' ? `&decision=${filter.toUpperCase()}` : ''}`)
          .then(r => r.ok ? r.json() : null),
      ]);
      if (s) setStatus(s);
      if (d) { setDecisions(d.decisions || []); setCounts(d.counts || {}); }
    } catch (_) { /* ignore */ }
  }, [filter]);

  useEffect(() => {
    load();
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, [load]);

  const control = async (action) => {
    setBusy(true);
    try {
      await fetch(`${BACKEND_URL}/api/funds/daemon/control`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      await load();
    } finally { setBusy(false); }
  };

  if (!status) return null;
  const s = status.state || {};
  const isRunning = s.status === 'running';

  return (
    <Card className="p-4 mb-4 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]" data-testid="fund-daemon-panel">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Cpu className={`w-4 h-4 ${isRunning ? 'text-emerald-400 animate-pulse' : 'text-[hsl(var(--muted-foreground))]'}`} />
          <h2 className="text-sm font-display font-semibold">NIFTY-500 Auto-Research Daemon</h2>
          <span className={`text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${
            isRunning ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/5' :
            s.status === 'paused' ? 'border-amber-500/40 text-amber-300 bg-amber-500/5' :
            'border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]'
          }`}>{s.status || 'unknown'}</span>
        </div>
        <div className="flex items-center gap-1">
          <button data-testid="daemon-start-btn"
                  onClick={() => control('start')}
                  disabled={busy || isRunning}
                  className="px-2 py-1 rounded text-[10px] bg-[hsl(var(--surface-2))] hover:bg-emerald-500/20 disabled:opacity-40 flex items-center gap-1">
            <Play className="w-3 h-3" /> Start
          </button>
          <button data-testid="daemon-pause-btn"
                  onClick={() => control('pause')}
                  disabled={busy || !isRunning}
                  className="px-2 py-1 rounded text-[10px] bg-[hsl(var(--surface-2))] hover:bg-amber-500/20 disabled:opacity-40 flex items-center gap-1">
            <Pause className="w-3 h-3" /> Pause
          </button>
          <button onClick={load} className="p-1 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]">
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-[10px] font-mono mb-3">
        <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
          <div className="text-[hsl(var(--muted-foreground))]">Now analyzing</div>
          <div className="text-[hsl(var(--foreground))] truncate">{s.current_symbol || '—'}</div>
        </div>
        <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
          <div className="text-[hsl(var(--muted-foreground))]">Queued</div>
          <div className="text-[hsl(var(--foreground))]">{status.queued ?? 0}</div>
        </div>
        <div className="p-2 rounded bg-emerald-500/5 border border-emerald-500/20">
          <div className="text-emerald-400/70">Accepts</div>
          <div className="text-emerald-300">{s.accepts ?? 0}</div>
        </div>
        <div className="p-2 rounded bg-red-500/5 border border-red-500/20">
          <div className="text-red-400/70">Rejects</div>
          <div className="text-red-300">{s.rejects ?? 0}</div>
        </div>
        <div className="p-2 rounded bg-amber-500/5 border border-amber-500/20">
          <div className="text-amber-400/70">Holds</div>
          <div className="text-amber-300">{s.holds ?? 0}</div>
        </div>
        <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
          <div className="text-[hsl(var(--muted-foreground))]">Total cycles</div>
          <div className="text-[hsl(var(--foreground))]">{s.cycle_count ?? 0}</div>
        </div>
      </div>

      <div className="flex items-center gap-1 mb-2">
        <History className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
        <span className="text-xs font-medium">Decision feed</span>
        <div className="flex-1" />
        {['all', 'accept', 'reject', 'hold'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
                  data-testid={`daemon-filter-${f}`}
                  className={`text-[10px] px-2 py-0.5 rounded ${
                    filter === f ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                 : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))]'
                  }`}>{f}</button>
        ))}
      </div>

      <div className="max-h-72 overflow-y-auto rounded border border-[hsl(var(--border))]" data-testid="daemon-decisions-list">
        {decisions.length === 0 ? (
          <p className="text-[11px] text-[hsl(var(--muted-foreground))] p-3">
            {isRunning ? 'Daemon is warming up — first decision arrives in ~60s.' : 'No decisions yet.'}
          </p>
        ) : (
          <table className="w-full text-[11px] font-mono">
            <thead className="bg-[hsl(var(--surface-2))] sticky top-0">
              <tr className="text-[hsl(var(--muted-foreground))] text-left">
                <th className="px-2 py-1 font-normal">Time</th>
                <th className="px-2 py-1 font-normal">Symbol</th>
                <th className="px-2 py-1 font-normal">Decision</th>
                <th className="px-2 py-1 font-normal">Verdict</th>
                <th className="px-2 py-1 font-normal text-right">Conf</th>
                <th className="px-2 py-1 font-normal">Headline</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d) => (
                <tr key={d.run_id} className="border-t border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]">
                  <td className="px-2 py-1 text-[hsl(var(--muted-foreground))] whitespace-nowrap">{(d.ts || '').slice(11, 19)}</td>
                  <td className="px-2 py-1 text-[hsl(var(--foreground))]">{d.symbol}</td>
                  <td className="px-2 py-1">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider border ${
                      d.decision === 'ACCEPT' ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/5' :
                      d.decision === 'REJECT' ? 'border-red-500/40 text-red-300 bg-red-500/5' :
                      'border-amber-500/40 text-amber-300 bg-amber-500/5'
                    }`}>{d.decision}</span>
                  </td>
                  <td className="px-2 py-1 text-[hsl(var(--muted-foreground))]">{d.final_verdict}</td>
                  <td className="px-2 py-1 text-right text-[hsl(var(--muted-foreground))]">
                    {d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}
                  </td>
                  <td className="px-2 py-1 text-[hsl(var(--muted-foreground))] truncate max-w-[280px]">
                    {(d.headline || '').slice(0, 90)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="mt-2 text-[10px] text-[hsl(var(--muted-foreground))]">
        Daemon feeds top NIFTY-500 stocks (by traded value) into the 6-agent pipeline one at a time. Each verdict + reasoning is persisted to <code>fund_decisions</code>.
      </p>
    </Card>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────
export default function FundManagement() {
  const [symbol, setSymbol] = useState('');
  const [horizon, setHorizon] = useState('swing');
  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState(null);
  const [run, setRun] = useState(null); // {stages, status, final_verdict, ...}
  const [error, setError] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);
  const eventSourceRef = useRef(null);

  const loadRecentRuns = useCallback(async () => {
    try {
      const r = await fetch(`${BACKEND_URL}/api/funds/runs?limit=8`);
      if (r.ok) {
        const j = await r.json();
        setRecentRuns(j.runs || []);
      }
    } catch (_) { /* ignore */ }
  }, []);

  useEffect(() => { loadRecentRuns(); }, [loadRecentRuns]);

  const cleanupSse = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };
  useEffect(() => () => cleanupSse(), []);

  const startAnalysis = async () => {
    const sym = symbol.trim().toUpperCase();
    if (!sym) { setError('Enter a symbol like RELIANCE or TCS.NS'); return; }
    cleanupSse();
    setError(null);
    setRunning(true);
    setRun({ symbol: sym, status: 'running', current_stage: 'queued', stages: {} });
    setRunId(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/funds/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym, horizon_hint: horizon }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const j = await res.json();
      setRunId(j.run_id);
      attachSse(j.run_id, sym);
    } catch (e) {
      setError(e.message || 'Failed to start analysis');
      setRunning(false);
    }
  };

  const attachSse = (id, sym) => {
    const url = `${BACKEND_URL}/api/funds/stream/${id}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.addEventListener('stage', (ev) => {
      try {
        const data = JSON.parse(ev.data);
        const { stage, ...rest } = data;
        setRun((prev) => {
          const stages = { ...(prev?.stages || {}), [stage]: { ...(prev?.stages?.[stage] || {}), ...rest } };
          return { ...(prev || { symbol: sym }), stages, current_stage: stage };
        });
      } catch (_) { /* ignore */ }
    });

    es.addEventListener('done', (ev) => {
      try {
        const data = JSON.parse(ev.data);
        setRun((prev) => ({ ...(prev || {}), status: data.status, final_verdict: data.final_verdict }));
      } catch (_) { /* ignore */ }
      setRunning(false);
      cleanupSse();
      loadRecentRuns();
    });

    es.addEventListener('error', () => {
      // EventSource auto-retries on transient errors; only stop if explicit error event came as data
      cleanupSse();
      setRunning(false);
    });
  };

  const reattach = async (id) => {
    cleanupSse();
    setError(null);
    setRunId(id);
    try {
      const r = await fetch(`${BACKEND_URL}/api/funds/runs/${id}`);
      if (!r.ok) throw new Error('Run not found');
      const j = await r.json();
      setRun(j);
      setSymbol(j.symbol || '');
      if (j.status === 'running') {
        setRunning(true);
        attachSse(id, j.symbol);
      }
    } catch (e) { setError(e.message); }
  };

  const stageStatus = (key) => run?.stages?.[key]?.status || (run?.current_stage === key ? 'running' : 'pending');
  const dataGather = run?.stages?.data_gathering;
  const analysts = run?.stages?.analysts;
  const debate = run?.stages?.debate;
  const trader = run?.stages?.trader;
  const risk = run?.stages?.risk;
  const fmgr = run?.stages?.fund_manager || run?.final_verdict;

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] p-4 sm:p-6 lg:p-8" data-testid="fund-management-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Briefcase className="w-7 h-7 text-[hsl(var(--primary))]" />
            <div>
              <h1 className="text-2xl font-display font-semibold text-[hsl(var(--foreground))]">Fund Management</h1>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                6-agent autonomous research desk · TradingAgents-style hierarchical pipeline · Indian equities (NSE/BSE)
              </p>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono">
            <Sparkles className="w-3 h-3 mr-1" />
            Claude Sonnet 4.5
          </Badge>
        </div>

        {/* Controls */}
        <Card className="p-4 mb-4 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]">
          <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-end">
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Symbol</label>
              <input
                data-testid="fund-symbol-input"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                onKeyDown={(e) => { if (e.key === 'Enter' && !running) startAnalysis(); }}
                placeholder="RELIANCE, TCS, INFY, 500325.BO …"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))] focus:outline-none focus:border-[hsl(var(--primary))] font-mono"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Horizon</label>
              <select
                data-testid="fund-horizon-select"
                value={horizon}
                onChange={(e) => setHorizon(e.target.value)}
                className="mt-1 w-full sm:w-36 px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))] focus:outline-none focus:border-[hsl(var(--primary))]"
              >
                <option value="short_term">Short-term</option>
                <option value="swing">Swing</option>
                <option value="long_term">Long-term</option>
              </select>
            </div>
            <button
              data-testid="fund-run-btn"
              onClick={startAnalysis}
              disabled={running || !symbol.trim()}
              className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {running ? 'Running…' : 'Run Analysis'}
            </button>
          </div>
          {error && (
            <div className="mt-2 text-xs text-red-400 flex items-center gap-1.5" data-testid="fund-error">
              <AlertCircle className="w-3.5 h-3.5" /> {error}
            </div>
          )}
        </Card>

        {/* Daemon: live NIFTY-500 churn */}
        <DaemonPanel />

        {/* Pipeline stepper */}
        {run && (
          <div className="flex items-center gap-1 mb-4 overflow-x-auto" data-testid="fund-pipeline-stepper">
            {STAGES.map((s, idx) => {
              const st = stageStatus(s.key);
              const StageIcon = s.icon;
              return (
                <React.Fragment key={s.key}>
                  <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[11px] whitespace-nowrap ${
                    st === 'done' ? 'border-emerald-500/40 bg-emerald-500/5 text-emerald-300' :
                    st === 'running' ? 'border-[hsl(var(--primary))]/50 bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]' :
                    st === 'error' ? 'border-red-500/40 bg-red-500/5 text-red-300' :
                    'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))]'
                  }`} data-testid={`stage-pill-${s.key}`}>
                    <StageIcon className="w-3.5 h-3.5" />
                    <span>{s.label}</span>
                    <StageDot status={st} />
                  </div>
                  {idx < STAGES.length - 1 && <div className="w-3 h-px bg-[hsl(var(--border))]" />}
                </React.Fragment>
              );
            })}
          </div>
        )}

        {/* Output grid */}
        {run && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3" data-testid="fund-output-grid">
            {/* Left/middle 2 cols: agent outputs */}
            <div className="lg:col-span-2 space-y-3">
              {/* Data summary */}
              {dataGather && (
                <Card className="p-3 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]">
                  <div className="flex items-center justify-between text-[11px] font-mono text-[hsl(var(--muted-foreground))]">
                    <div className="flex items-center gap-1.5 text-[hsl(var(--foreground))] font-medium text-xs">
                      <Activity className="w-3.5 h-3.5 text-[hsl(var(--primary))]" /> Data Gathering
                    </div>
                    <div className="flex items-center gap-3">
                      <span>fundamentals: <span className={dataGather.fundamentals_ok ? 'text-emerald-400' : 'text-red-400'}>{dataGather.fundamentals_ok ? '✓' : '×'}</span></span>
                      <span>technicals: <span className={dataGather.technicals_ok ? 'text-emerald-400' : 'text-red-400'}>{dataGather.technicals_ok ? '✓' : '×'}</span></span>
                      <span>news: <span className="text-[hsl(var(--foreground))]">{dataGather.news_count ?? 0}</span></span>
                      <span>reg-hits: <span className="text-[hsl(var(--foreground))]">{dataGather.compliance_hits ?? 0}</span></span>
                    </div>
                  </div>
                </Card>
              )}

              {/* Analysts */}
              {analysts && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <AnalystCard title="Fundamentals" icon={Brain} data={analysts.fundamentals} />
                  <AnalystCard title="Sentiment" icon={Activity} data={analysts.sentiment} />
                  <AnalystCard title="News" icon={Newspaper} data={analysts.news} />
                  <AnalystCard title="Technical" icon={LineChartIcon} data={analysts.technical} />
                </div>
              )}

              {/* Debate */}
              {debate && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <DebateCard side="Bull" data={debate.bull} />
                  <DebateCard side="Bear" data={debate.bear} />
                </div>
              )}

              {/* Trader + Risk */}
              {trader && <TraderCard data={trader} />}
              {risk && <RiskCard data={risk} />}
            </div>

            {/* Right column: final verdict + recent runs */}
            <div className="space-y-3">
              {fmgr && <FundManagerCard data={fmgr} symbol={run.symbol} />}

              <Card className="p-3 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-[hsl(var(--foreground))]">
                    <Clock className="w-3.5 h-3.5 text-[hsl(var(--primary))]" /> Recent Runs
                  </div>
                  <button onClick={loadRecentRuns} className="text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]" data-testid="fund-runs-refresh">
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </div>
                {recentRuns.length === 0 ? (
                  <p className="text-[11px] text-[hsl(var(--muted-foreground))]">No previous runs yet.</p>
                ) : (
                  <ul className="space-y-1" data-testid="fund-runs-list">
                    {recentRuns.map((r) => (
                      <li key={r.run_id}>
                        <button
                          onClick={() => reattach(r.run_id)}
                          className={`w-full text-left px-2 py-1.5 rounded text-[11px] hover:bg-[hsl(var(--surface-2))] flex items-center justify-between ${runId === r.run_id ? 'bg-[hsl(var(--surface-2))]' : ''}`}
                        >
                          <span className="font-mono text-[hsl(var(--foreground))] truncate">{r.symbol}</span>
                          <span className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))]">
                            {r.final_verdict?.final_verdict && <VerdictBadge value={r.final_verdict.final_verdict} />}
                            <span className={`w-1.5 h-1.5 rounded-full ${
                              r.status === 'completed' ? 'bg-emerald-400' :
                              r.status === 'error' ? 'bg-red-400' :
                              'bg-[hsl(var(--primary))] animate-pulse'
                            }`} />
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <p className="text-[10px] text-[hsl(var(--muted-foreground))] leading-relaxed px-1">
                Read-only research desk. Verdicts are AI-generated and not investment advice. Always consult a SEBI-registered advisor before acting.
              </p>
            </div>
          </div>
        )}

        {!run && !running && (
          <Card className="p-8 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] text-center mt-4" data-testid="fund-empty-state">
            <Briefcase className="w-10 h-10 text-[hsl(var(--primary))]/40 mx-auto mb-3" />
            <p className="text-sm text-[hsl(var(--foreground))] font-medium">Spin up the research desk</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 max-w-md mx-auto">
              Enter an Indian-equity symbol to dispatch 4 analysts, a bull/bear debate, a trader, the risk desk and the fund manager — all running on Claude Sonnet 4.5.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import {
  ArrowLeft, RefreshCw, Loader2, TrendingUp, TrendingDown, IndianRupee,
  Shield, Zap, Target, Rocket, ArrowRightLeft, Gem, BarChart3, Brain,
  History, Crosshair, ArrowUpRight, ArrowDownRight, ChevronRight, ChevronDown
} from 'lucide-react';
import {
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Area, AreaChart, ComposedChart, Line, BarChart, Bar,
  ReferenceLine, Legend
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SECTOR_COLORS = [
  '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16',
];

const STRATEGY_ICONS = {
  bespoke_forward_looking: Rocket, quick_entry: Zap, long_term: Shield,
  swing: ArrowRightLeft, alpha_generator: Target, value_stocks: Gem,
};

const STRATEGY_COLORS = {
  bespoke_forward_looking: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
  quick_entry: 'from-amber-500/20 to-orange-500/20 border-amber-500/30',
  long_term: 'from-emerald-500/20 to-green-500/20 border-emerald-500/30',
  swing: 'from-purple-500/20 to-violet-500/20 border-purple-500/30',
  alpha_generator: 'from-red-500/20 to-rose-500/20 border-red-500/30',
  value_stocks: 'from-teal-500/20 to-cyan-500/20 border-teal-500/30',
};

// ═══════════════════════════════════════════
// SIGNAL BADGE
// ═══════════════════════════════════════════
function SignalBadge({ pnl }) {
  const signal = pnl > 5 ? 'BULLISH' : pnl < -5 ? 'BEARISH' : 'NEUTRAL';
  const cls = signal === 'BULLISH' ? 'bg-emerald-500/15 text-emerald-400' :
              signal === 'BEARISH' ? 'bg-red-500/15 text-red-400' :
              'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]';
  return <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${cls}`}>{signal}</span>;
}

// ═══════════════════════════════════════════
// HOLDINGS TABLE
// ═══════════════════════════════════════════
function HoldingsTable({ holdings }) {
  if (!holdings?.length) return <p className="text-xs text-[hsl(var(--muted-foreground))] p-4">No holdings</p>;
  return (
    <div className="overflow-x-auto" data-testid="holdings-table">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
            <th className="py-2 px-3 text-left">Stock</th>
            <th className="py-2 px-3 text-left">Sector</th>
            <th className="py-2 px-3 text-right">Entry</th>
            <th className="py-2 px-3 text-right">Current</th>
            <th className="py-2 px-3 text-right">P&L %</th>
            <th className="py-2 px-3 text-right">Weight</th>
            <th className="py-2 px-3 text-right">Value</th>
            <th className="py-2 px-3 text-center">Signal</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => {
            const pnl = h.pnl_pct || 0;
            return (
              <tr key={i} className="border-b border-[hsl(var(--border))]/30 hover:bg-[hsl(var(--surface-2))]">
                <td className="py-2 px-3">
                  <p className="font-mono font-medium">{(h.symbol || '').replace('.NS', '')}</p>
                  {h.quantity && <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Qty: {h.quantity}</p>}
                </td>
                <td className="py-2 px-3"><span className="text-[10px] bg-[hsl(var(--surface-3))] px-1.5 py-0.5 rounded">{h.sector || 'N/A'}</span></td>
                <td className="py-2 px-3 text-right font-mono">{h.entry_price?.toFixed(2)}</td>
                <td className="py-2 px-3 text-right font-mono">{h.current_price?.toFixed(2) || '--'}</td>
                <td className={`py-2 px-3 text-right font-mono font-bold ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}%
                </td>
                <td className="py-2 px-3 text-right font-mono">{h.weight?.toFixed(1)}%</td>
                <td className="py-2 px-3 text-right font-mono">{(((h.value || 0) > 0 ? h.value : (h.current_price || h.entry_price || 0) * (h.quantity || 0)) / 1e5).toFixed(2)}L</td>
                <td className="py-2 px-3 text-center"><SignalBadge pnl={pnl} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ═══════════════════════════════════════════
// REBALANCE LOG
// ═══════════════════════════════════════════
function RebalanceLog({ strategyType }) {
  const [logs, setLogs] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portfolios/rebalance-log/${strategyType}?limit=20`)
      .then(r => r.json())
      .then(d => setLogs(d.logs || []))
      .catch(() => {});
  }, [strategyType]);

  const swapLogs = logs.filter(l => l.action === 'REBALANCE' && l.changes?.length > 0);
  if (swapLogs.length === 0) return null;

  return (
    <div data-testid="rebalance-log">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 mb-2 w-full text-left">
        <ArrowRightLeft className="w-4 h-4 text-amber-400" />
        <p className="text-sm font-semibold text-[hsl(var(--foreground))]">Rebalance History</p>
        <span className="text-[10px] bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded-full font-mono">{swapLogs.length} swap{swapLogs.length !== 1 ? 's' : ''}</span>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))] ml-auto" /> : <ChevronRight className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))] ml-auto" />}
      </button>
      {open && (
        <div className="space-y-3">
          {swapLogs.map((log, i) => (
            <Card key={i} className="bg-[hsl(var(--surface-1))] border-amber-500/20 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] text-amber-400 font-mono">
                  {log.timestamp ? new Date(log.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recent'}
                </span>
                <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{log.changes?.length} changes</span>
              </div>
              <div className="space-y-2">
                {(log.changes || []).map((ch, j) => (
                  <div key={j} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]/30">
                    {ch.type === 'IN' ? (
                      <span className="text-emerald-400 text-[10px] font-mono font-bold w-8">+ IN</span>
                    ) : (
                      <span className="text-red-400 text-[10px] font-mono font-bold w-8">- OUT</span>
                    )}
                    <div className="flex-1">
                      <span className="font-mono font-medium">{(ch.symbol || '').replace('.NS', '')}</span>
                      {ch.sector && <span className="ml-2 text-[10px] text-[hsl(var(--muted-foreground))]">{ch.sector}</span>}
                    </div>
                    {ch.rationale && (
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] max-w-[250px] truncate">{ch.rationale}</p>
                    )}
                  </div>
                ))}
              </div>
              {log.rationale && (
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-2 italic border-t border-[hsl(var(--border))]/30 pt-2">{log.rationale}</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════
// AI CONSTRUCTION NOTES
// ═══════════════════════════════════════════
function ConstructionNotes({ portfolio }) {
  const [open, setOpen] = useState(false);
  const notes = portfolio?.construction_log || portfolio?.ai_rationale || portfolio?.rationale;
  const models = portfolio?.construction_log?.models_succeeded || portfolio?.models_used;
  if (!notes && !models) return null;

  const rationale = typeof notes === 'string' ? notes : notes?.rationale || notes?.thesis || '';
  const modelList = models || notes?.models_succeeded || [];

  if (!rationale && modelList.length === 0) return null;

  return (
    <div data-testid="construction-notes">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 mb-2 w-full text-left">
        <Brain className="w-4 h-4 text-[hsl(var(--primary))]" />
        <p className="text-sm font-semibold text-[hsl(var(--foreground))]">AI Construction Notes</p>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))] ml-auto" /> : <ChevronRight className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))] ml-auto" />}
      </button>
      {open && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
          {modelList.length > 0 && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] text-[hsl(var(--muted-foreground))]">Models:</span>
              {(Array.isArray(modelList) ? modelList : []).map(m => (
                <span key={m} className="text-[9px] bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] px-1.5 py-0.5 rounded font-mono">{m}</span>
              ))}
            </div>
          )}
          {rationale && <p className="text-xs text-[hsl(var(--foreground))]/80 leading-relaxed whitespace-pre-line">{rationale}</p>}
        </Card>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════
// SECTOR PIE
// ═══════════════════════════════════════════
function SectorPie({ holdings }) {
  const sectors = {};
  (holdings || []).forEach(h => {
    const s = h.sector || 'Other';
    // Use value if available, fall back to weight * entry_price * quantity, then weight
    const val = (h.value && h.value > 0) ? h.value :
                (h.entry_price && h.quantity) ? h.entry_price * h.quantity :
                (h.weight || 10);
    sectors[s] = (sectors[s] || 0) + val;
  });
  const total = Object.values(sectors).reduce((a, b) => a + b, 0) || 1;
  const data = Object.entries(sectors).map(([name, val]) => ({ name, value: val, pct: ((val / total) * 100).toFixed(1) })).sort((a, b) => b.value - a.value);
  if (!data.length) return null;

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="sector-allocation">
      <p className="text-xs font-semibold text-[hsl(var(--foreground))] mb-3">Sector Allocation</p>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width={160} height={160}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" stroke="none">
              {data.map((_, i) => <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
              formatter={(val) => [`₹${(val / 1e5).toFixed(1)}L`]} />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex-1 space-y-1.5">
          {data.map((s, i) => (
            <div key={s.name} className="flex items-center justify-between text-[10px]">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                <span className="text-[hsl(var(--foreground))]">{s.name}</span>
              </div>
              <span className="font-mono font-bold text-[hsl(var(--foreground))]">{s.pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════
// BACKTEST
// ═══════════════════════════════════════════
function BacktestSection({ strategyType }) {
  const [bt, setBt] = useState(null);
  const [computing, setComputing] = useState(false);

  const fetchBt = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portfolios/backtest/${strategyType}`);
      const d = await res.json();
      if (d.status === 'computing') { setComputing(true); return false; }
      if (!d.error) setBt(d);
      setComputing(false);
      return true;
    } catch { setComputing(false); return true; }
  }, [strategyType]);

  useEffect(() => { fetchBt(); }, [fetchBt]);
  useEffect(() => {
    if (!computing) return;
    const iv = setInterval(async () => { if (await fetchBt()) clearInterval(iv); }, 10000);
    return () => clearInterval(iv);
  }, [computing, fetchBt]);

  if (!bt && !computing) return null;
  if (computing) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
      <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--primary))]" /><span className="text-xs text-[hsl(var(--muted-foreground))]">Computing 5Y backtest... auto-refreshing</span></div>
    </Card>
  );

  const isAlpha = (bt.alpha_pct || 0) > 0;
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="backtest-section">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[hsl(var(--primary))]" />
          <p className="text-xs font-semibold text-[hsl(var(--foreground))]">5-Year Backtest</p>
          <span className="text-[9px] text-[hsl(var(--muted-foreground))]">{bt.years}Y | {bt.stocks_tested} stocks | {bt.months} months</span>
        </div>
        <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${isAlpha ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
          Alpha: {bt.alpha_pct >= 0 ? '+' : ''}{bt.alpha_pct}%
        </span>
      </div>
      {bt.chart_data?.length > 2 && (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={bt.chart_data} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
            <defs>
              <linearGradient id="btGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 14% 14%)" />
            <XAxis dataKey="month" tick={{ fontSize: 9, fill: 'hsl(215 16% 70%)' }} interval={Math.floor(bt.chart_data.length / 8)} />
            <YAxis tick={{ fontSize: 9, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} />
            <Tooltip contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }} formatter={v => [`${v.toFixed(1)}%`]} />
            <Area type="monotone" dataKey="portfolio" stroke="#10b981" fill="url(#btGrad)" strokeWidth={2} name="Portfolio" />
            <Area type="monotone" dataKey="nifty50" stroke="#f59e0b" fill="none" strokeWidth={1} strokeDasharray="4 4" name="Nifty 50" />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
          </AreaChart>
        </ResponsiveContainer>
      )}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mt-3">
        {[
          { l: 'CAGR', v: `${bt.cagr_pct >= 0 ? '+' : ''}${bt.cagr_pct}%`, c: bt.cagr_pct >= 0 ? 'text-emerald-400' : 'text-red-400' },
          { l: 'Max DD', v: `${bt.max_drawdown_pct}%`, c: 'text-red-400' },
          { l: 'Sharpe', v: bt.sharpe_ratio, c: bt.sharpe_ratio >= 1 ? 'text-emerald-400' : 'text-amber-400' },
          { l: 'Win Rate', v: `${bt.win_rate_monthly_pct}%`, c: bt.win_rate_monthly_pct >= 55 ? 'text-emerald-400' : 'text-[hsl(var(--foreground))]' },
          { l: 'Volatility', v: `${bt.annual_volatility_pct}%`, c: 'text-[hsl(var(--foreground))]' },
          { l: 'Nifty 50', v: `+${bt.benchmark_cagr_pct}%`, c: 'text-amber-400' },
        ].map(m => (
          <div key={m.l}>
            <p className="text-[9px] text-[hsl(var(--muted-foreground))]">{m.l}</p>
            <p className={`text-sm font-mono font-bold ${m.c}`}>{m.v}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════
// SIMULATION
// ═══════════════════════════════════════════
function SimulationSection({ strategyType }) {
  const [sim, setSim] = useState(null);
  const [computing, setComputing] = useState(false);

  const fetchSim = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portfolios/simulation/${strategyType}`);
      const d = await res.json();
      if (d.status === 'computing') { setComputing(true); return false; }
      if (!d.error) setSim(d);
      setComputing(false);
      return true;
    } catch { setComputing(false); return true; }
  }, [strategyType]);

  useEffect(() => { fetchSim(); }, [fetchSim]);
  useEffect(() => {
    if (!computing) return;
    const iv = setInterval(async () => { if (await fetchSim()) clearInterval(iv); }, 15000);
    return () => clearInterval(iv);
  }, [computing, fetchSim]);

  if (!sim && !computing) return null;
  if (computing) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
      <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-cyan-400" /><span className="text-xs text-[hsl(var(--muted-foreground))]">Training 4-model ensemble + 10K Monte Carlo... auto-refreshing</span></div>
    </Card>
  );

  const mc = sim.monte_carlo || {};
  const rm = mc.risk_metrics || {};
  const fc = mc.fan_chart || [];
  const dc = mc.distribution_chart || [];
  const lstm = sim.lstm_forecast || {};
  const ts = mc.terminal_stats || {};

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="simulation-section">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-cyan-400" />
          <p className="text-xs font-semibold text-[hsl(var(--foreground))]">Forward Simulation</p>
          <span className="text-[9px] bg-cyan-500/10 text-cyan-400 px-1.5 py-0.5 rounded font-mono">Ensemble + MC</span>
        </div>
        <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${rm.expected_return_pct > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
          E[R]: {(rm.expected_return_pct || 0) >= 0 ? '+' : ''}{rm.expected_return_pct}%
        </span>
      </div>
      {/* Fan Chart */}
      {fc.length > 2 && (
        <div className="mb-3">
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] mb-1 uppercase tracking-wider">1-Year Forward Projection</p>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={fc} margin={{ top: 5, right: 5, bottom: 5, left: -5 }}>
              <defs>
                <linearGradient id="fanInner" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 14% 14%)" />
              <XAxis dataKey="week" tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `W${v}`} interval={Math.max(1, Math.floor(fc.length / 8))} />
              <YAxis tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${(v / 1e5).toFixed(1)}L`} />
              <Tooltip contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
                formatter={(val, name) => [`₹${(val / 1e5).toFixed(2)}L`, { p5: '5th', p25: '25th', p50: 'Median', p75: '75th', p95: '95th', mean: 'Mean' }[name] || name]} />
              <Area type="monotone" dataKey="p95" stroke="none" fill="hsla(186,92%,42%,0.05)" />
              <Area type="monotone" dataKey="p5" stroke="none" fill="hsl(222 18% 8%)" />
              <Area type="monotone" dataKey="p75" stroke="none" fill="url(#fanInner)" />
              <Area type="monotone" dataKey="p25" stroke="none" fill="hsl(222 18% 8%)" />
              <Line type="monotone" dataKey="p50" stroke="#06b6d4" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="mean" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4 4" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
      {/* Distribution */}
      {dc.length > 2 && (
        <div className="mb-3">
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] mb-1 uppercase tracking-wider">Terminal Return Distribution</p>
          <ResponsiveContainer width="100%" height={80}>
            <BarChart data={dc} margin={{ top: 2, right: 5, bottom: 2, left: -15 }}>
              <XAxis dataKey="return_pct" tick={{ fontSize: 7, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} interval={Math.floor(dc.length / 5)} />
              <YAxis tick={false} width={10} />
              <ReferenceLine x={0} stroke="hsl(215 16% 50%)" strokeDasharray="2 2" />
              <Bar dataKey="frequency">{dc.map((e, i) => <Cell key={i} fill={e.return_pct >= 0 ? 'hsla(186,92%,42%,0.6)' : 'hsla(0,72%,52%,0.5)'} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {/* Risk metrics */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {[
          { l: 'VaR 95%', v: `${rm.var_95_pct}%`, c: 'text-red-400' },
          { l: 'CVaR 95%', v: `${rm.cvar_95_pct}%`, c: 'text-red-400' },
          { l: 'Max Exp DD', v: `-${rm.max_expected_drawdown_pct}%`, c: 'text-red-400' },
          { l: 'Median Ret', v: `${(rm.median_return_pct || 0) >= 0 ? '+' : ''}${rm.median_return_pct}%`, c: (rm.median_return_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400' },
          { l: 'P(Profit)', v: `${rm.probability_of_profit_pct}%`, c: rm.probability_of_profit_pct >= 60 ? 'text-emerald-400' : 'text-amber-400' },
          { l: 'LSTM Vol', v: `${lstm.annualized_volatility_pct}%`, c: 'text-[hsl(var(--foreground))]' },
        ].map(m => (
          <div key={m.l}>
            <p className="text-[9px] text-[hsl(var(--muted-foreground))]">{m.l}</p>
            <p className={`text-sm font-mono font-bold ${m.c}`}>{m.v}</p>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-[hsl(var(--border))]/50 text-[9px] text-[hsl(var(--muted-foreground))]">
        <span>Worst: ₹{(ts.worst_case_value / 1e5).toFixed(1)}L</span>
        <span className="text-cyan-400 font-mono font-semibold">Median: ₹{(ts.median_value / 1e5).toFixed(1)}L</span>
        <span>Best: ₹{(ts.best_case_value / 1e5).toFixed(1)}L</span>
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════
// WALK-FORWARD
// ═══════════════════════════════════════════
function WalkForwardSection({ strategyType }) {
  const [records, setRecords] = useState([]);
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portfolios/walk-forward/${strategyType}`)
      .then(r => r.json()).then(d => setRecords(d.records || [])).catch(() => {});
  }, [strategyType]);

  if (!records.length) return null;
  const latest = records[records.length - 1];
  const f = latest.forecast || {};
  const a = latest.actual || {};
  const dev = (f.expected_return_pct || 0) - (a.total_pnl_pct || 0);

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="walk-forward-section">
      <div className="flex items-center gap-2 mb-3">
        <Crosshair className="w-4 h-4 text-amber-400" />
        <p className="text-xs font-semibold text-[hsl(var(--foreground))]">Walk-Forward Tracking</p>
        <span className="text-[9px] text-[hsl(var(--muted-foreground))] font-mono">{records.length} snapshots</span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-cyan-500/5 rounded-lg p-3 border border-cyan-500/10">
          <p className="text-[9px] text-cyan-400 uppercase tracking-wider mb-1">Forecast (MC)</p>
          <p className="text-lg font-mono font-bold text-cyan-400">{f.expected_return_pct >= 0 ? '+' : ''}{f.expected_return_pct?.toFixed(1)}%</p>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">P(Profit): {f.probability_of_profit_pct?.toFixed(0)}%</p>
        </div>
        <div className="bg-emerald-500/5 rounded-lg p-3 border border-emerald-500/10">
          <p className="text-[9px] text-emerald-400 uppercase tracking-wider mb-1">Actual (Live)</p>
          <p className={`text-lg font-mono font-bold ${(a.total_pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {(a.total_pnl_pct || 0) >= 0 ? '+' : ''}{(a.total_pnl_pct || 0).toFixed(2)}%
          </p>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">₹{a.portfolio_value ? (a.portfolio_value / 1e5).toFixed(1) + 'L' : '--'}</p>
        </div>
        <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-[hsl(var(--border))]">
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-1">Deviation</p>
          <p className={`text-lg font-mono font-bold ${Math.abs(dev) < 10 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {dev >= 0 ? '+' : ''}{dev.toFixed(1)}%
          </p>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">VaR 95%: {f.var_95_pct?.toFixed(1)}%</p>
        </div>
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════
export default function PortfolioDetail() {
  const { type } = useParams();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [strategies, setStrategies] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${BACKEND_URL}/api/portfolios`);
        const d = await res.json();
        setStrategies(d.strategies || {});
        const p = (d.portfolios || []).find(p => p.type === type);
        setPortfolio(p || null);
      } catch { /* */ }
      setLoading(false);
    }
    load();
  }, [type]);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" />
    </div>
  );

  const cfg = strategies[type] || {};
  const Icon = STRATEGY_ICONS[type] || BarChart3;
  const colors = STRATEGY_COLORS[type] || '';
  const holdings = portfolio?.holdings || [];
  const isActive = portfolio?.status === 'active';
  const pnl = portfolio?.total_pnl || 0;
  const pnlPct = portfolio?.total_pnl_pct || 0;
  const invested = portfolio?.actual_invested || 0;
  const currentVal = portfolio?.current_value || invested;

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-6xl mx-auto" data-testid="portfolio-detail-page">
      {/* Back + Header */}
      <div>
        <button onClick={() => navigate('/watchlist')} className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] mb-3" data-testid="back-btn">
          <ArrowLeft className="w-3.5 h-3.5" /> All Portfolios
        </button>
        <div className={`p-5 rounded-xl border bg-gradient-to-br ${colors}`}>
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-lg bg-[hsl(var(--surface-1))] flex items-center justify-center">
                <Icon className="w-6 h-6 text-[hsl(var(--primary))]" />
              </div>
              <div>
                <h1 className="text-xl font-display font-bold text-[hsl(var(--foreground))]">{cfg.name || portfolio?.name || type}</h1>
                <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">{cfg.description || ''}</p>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{cfg.horizon || portfolio?.horizon}</span>
                  {portfolio?.pipeline && <span className="text-[9px] bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded font-mono">{portfolio.pipeline}</span>}
                  {portfolio?.last_rebalanced && (
                    <span className="text-[10px] text-amber-400/80 flex items-center gap-0.5">
                      <History className="w-2.5 h-2.5" />
                      Rebalanced {new Date(portfolio.last_rebalanced).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                    </span>
                  )}
                </div>
              </div>
            </div>
            {isActive && (
              <div className="text-right">
                <p className="text-2xl font-mono font-bold text-[hsl(var(--foreground))]">
                  <IndianRupee className="w-4 h-4 inline" />{currentVal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
                <p className={`text-sm font-mono flex items-center justify-end gap-0.5 ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pnl >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {pnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                  <span className="ml-1 text-xs">({pnl >= 0 ? '+' : ''}{pnl.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })})</span>
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{holdings.length} stocks | Invested: ₹{(invested / 1e5).toFixed(1)}L</p>
              </div>
            )}
          </div>
          {!isActive && (
            <p className="text-sm text-amber-400 mt-3">Portfolio not yet constructed or currently building.</p>
          )}
        </div>
      </div>

      {isActive && (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { l: 'Invested', v: `₹${(invested / 1e5).toFixed(1)}L` },
              { l: 'Current Value', v: `₹${(currentVal / 1e5).toFixed(1)}L` },
              { l: 'Holdings', v: holdings.length },
              { l: 'Top 3 Conc.', v: `${(holdings.slice(0, 3).reduce((s, h) => s + (h.weight || 0), 0)).toFixed(1)}%` },
            ].map(s => (
              <Card key={s.l} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-3">
                <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{s.l}</p>
                <p className="text-base font-mono font-bold text-[hsl(var(--foreground))]">{s.v}</p>
              </Card>
            ))}
          </div>

          {/* Holdings + Sector side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <HoldingsTable holdings={holdings} />
              </Card>
            </div>
            <SectorPie holdings={holdings} />
          </div>

          {/* Backtest + Simulation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <BacktestSection strategyType={type} />
            <SimulationSection strategyType={type} />
          </div>

          {/* Walk-Forward */}
          <WalkForwardSection strategyType={type} />

          {/* Rebalance Log + AI Notes */}
          <RebalanceLog strategyType={type} />
          <ConstructionNotes portfolio={portfolio} />
        </>
      )}
    </div>
  );
}

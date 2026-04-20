import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, BarChart3, TrendingUp, TrendingDown, Shield, Activity, Award, Loader2, History, Target, Brain, Zap, AlertTriangle, Percent, ChevronRight, RotateCcw, Crosshair } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { getUser } from '../components/TOTPGate';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend, LineChart, Line, CartesianGrid, Area, AreaChart, ComposedChart, ReferenceLine } from 'recharts';
import { ResponsiveContainer } from '../components/layout/SafeResponsiveContainer';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SECTOR_COLORS = [
  '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16',
  '#06b6d4', '#e11d48', '#a855f7', '#22d3ee', '#facc15',
];

const STRATEGY_COLORS = {
  bespoke_forward_looking: '#3b82f6',
  quick_entry: '#f59e0b',
  long_term: '#10b981',
  swing: '#8b5cf6',
  alpha_generator: '#ef4444',
  value_stocks: '#14b8a6',
};

function MetricCard({ label, value, suffix, color, icon: Icon }) {
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-1">
          {Icon && <Icon className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />}
          <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider">{label}</p>
        </div>
        <p className={`text-lg font-mono font-bold ${color || 'text-[hsl(var(--foreground))]'}`}>
          {value}{suffix || ''}
        </p>
      </CardContent>
    </Card>
  );
}

function SectorPieChart({ data, title }) {
  if (!data || data.length === 0) return null;

  return (
    <div data-testid="sector-pie-chart">
      <p className="text-xs font-semibold text-[hsl(var(--muted-foreground))] mb-3 uppercase tracking-wider">{title}</p>
      <div className="flex items-start gap-4">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey="pct" nameKey="sector" cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={2} stroke="none">
              {data.map((_, i) => <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />)}
            </Pie>
            <Tooltip
              contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '11px' }}
              itemStyle={{ color: 'hsl(210 20% 98%)' }}
              formatter={(val) => `${val}%`}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {data.map((item, i) => (
          <div key={item.sector} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
            <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{item.sector} ({item.pct}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PerformanceComparison({ portfolios }) {
  if (!portfolios || portfolios.length === 0) return null;

  const barData = portfolios.map(p => ({
    name: p.name?.replace(' ', '\n').substring(0, 12),
    type: p.type,
    pnl_pct: p.total_pnl_pct,
    win_rate: p.win_rate,
  }));

  return (
    <div data-testid="performance-comparison">
      <p className="text-xs font-semibold text-[hsl(var(--muted-foreground))] mb-3 uppercase tracking-wider">P&L by Strategy (%)</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 20 }}>
          <XAxis type="number" tick={{ fontSize: 10, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: 'hsl(215 16% 70%)' }} width={80} />
          <Tooltip
            contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '11px' }}
            itemStyle={{ color: 'hsl(210 20% 98%)' }}
            formatter={(val) => `${val}%`}
          />
          <Bar dataKey="pnl_pct" name="Return %">
            {barData.map((entry, i) => (
              <Cell key={i} fill={entry.pnl_pct >= 0 ? '#10b981' : '#ef4444'} radius={[0, 4, 4, 0]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RiskRadar({ portfolios }) {
  if (!portfolios || portfolios.length === 0) return null;

  const radarData = portfolios.filter(p => p.avg_beta !== null).map(p => ({
    strategy: p.name?.substring(0, 10),
    beta: p.avg_beta || 1,
    volatility: p.volatility || 0,
    concentration: p.top3_concentration || 0,
    win_rate: p.win_rate || 0,
  }));

  if (radarData.length === 0) return null;

  return (
    <div data-testid="risk-radar">
      <p className="text-xs font-semibold text-[hsl(var(--muted-foreground))] mb-3 uppercase tracking-wider">Risk Profile</p>
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={radarData}>
          <PolarGrid stroke="hsl(222 14% 18%)" />
          <PolarAngleAxis dataKey="strategy" tick={{ fontSize: 9, fill: 'hsl(215 16% 70%)' }} />
          <Radar name="Beta" dataKey="beta" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} />
          <Radar name="Win Rate" dataKey="win_rate" stroke="#10b981" fill="#10b981" fillOpacity={0.1} />
          <Legend wrapperStyle={{ fontSize: '10px' }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function PortfolioRiskTable({ portfolios }) {
  if (!portfolios || portfolios.length === 0) return null;

  return (
    <div data-testid="risk-metrics-table">
      <p className="text-xs font-semibold text-[hsl(var(--muted-foreground))] mb-3 uppercase tracking-wider">Risk Metrics by Strategy</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
              <th className="px-3 py-2 text-left">Strategy</th>
              <th className="px-3 py-2 text-right">Invested</th>
              <th className="px-3 py-2 text-right">Value</th>
              <th className="px-3 py-2 text-right">Return</th>
              <th className="px-3 py-2 text-right">Beta</th>
              <th className="px-3 py-2 text-right">Vol</th>
              <th className="px-3 py-2 text-right">Win%</th>
              <th className="px-3 py-2 text-right">Top3 Conc</th>
              <th className="px-3 py-2 text-right hidden sm:table-cell">Best</th>
              <th className="px-3 py-2 text-right hidden sm:table-cell">Worst</th>
              <th className="px-3 py-2 text-right hidden md:table-cell">Pipeline</th>
            </tr>
          </thead>
          <tbody>
            {portfolios.map((p) => (
              <tr key={p.type} className="border-b border-[hsl(var(--border))]/50 hover:bg-[hsl(var(--surface-2))]">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STRATEGY_COLORS[p.type] || '#888' }} />
                    <span className="text-xs font-semibold text-[hsl(var(--foreground))]">{p.name}</span>
                  </div>
                  <p className="text-[9px] text-[hsl(var(--muted-foreground))] ml-4">{p.horizon}</p>
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs">{(p.invested / 1e5).toFixed(1)}L</td>
                <td className="px-3 py-2 text-right font-mono text-xs">{(p.current_value / 1e5).toFixed(1)}L</td>
                <td className={`px-3 py-2 text-right font-mono text-xs font-bold ${p.total_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {p.total_pnl_pct >= 0 ? '+' : ''}{p.total_pnl_pct.toFixed(2)}%
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--foreground))]">{p.avg_beta ?? '—'}</td>
                <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--foreground))]">{p.volatility.toFixed(1)}</td>
                <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--foreground))]">{p.win_rate}%</td>
                <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--muted-foreground))]">{p.top3_concentration}%</td>
                <td className="px-3 py-2 text-right font-mono text-xs text-emerald-400 hidden sm:table-cell">
                  {p.top_performer ? `${p.top_performer.symbol} +${p.top_performer.pnl_pct}%` : '—'}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-red-400 hidden sm:table-cell">
                  {p.worst_performer ? `${p.worst_performer.symbol} ${p.worst_performer.pnl_pct}%` : '—'}
                </td>
                <td className="px-3 py-2 text-right hidden md:table-cell">
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${p.pipeline === 'hardened_v2' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]'}`}>
                    {p.pipeline === 'hardened_v2' ? 'v2' : 'v1'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SimulationCard({ strategyType, strategyName }) {
  const [sim, setSim] = useState(null);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState(null);

  const fetchSimulation = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portfolios/simulation/${strategyType}`);
      const d = await res.json();
      if (d.status === 'computing') {
        setComputing(true);
        setLoading(false);
        return false; // Not ready yet
      }
      if (d.error) {
        setError(d.error);
        setComputing(false);
        setLoading(false);
        return true;
      }
      setSim(d);
      setComputing(false);
      setLoading(false);
      return true;
    } catch (e) {
      setError('Failed to load simulation');
      setComputing(false);
      setLoading(false);
      return true;
    }
  }, [strategyType]);

  useEffect(() => {
    setLoading(true);
    fetchSimulation();
  }, [fetchSimulation]);

  // Poll while computing
  useEffect(() => {
    if (!computing) return;
    const interval = setInterval(async () => {
      const done = await fetchSimulation();
      if (done) clearInterval(interval);
    }, 15000);
    return () => clearInterval(interval);
  }, [computing, fetchSimulation]);

  if (loading || computing) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid={`simulation-loading-${strategyType}`}>
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          {computing ? 'Computing LSTM + 10K Monte Carlo paths...' : `Initializing simulation for ${strategyName}...`}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        <div className="h-2 bg-[hsl(var(--surface-2))] rounded animate-pulse w-3/4" />
        <div className="h-2 bg-[hsl(var(--surface-2))] rounded animate-pulse w-1/2" />
        {computing && <p className="text-[9px] text-[hsl(var(--muted-foreground))] mt-2">Training neural network on historical data... Auto-refreshing every 15s</p>}
      </div>
    </Card>
  );

  if (error || !sim) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid={`simulation-error-${strategyType}`}>
      <p className="text-xs text-[hsl(var(--muted-foreground))]">{strategyName}: {error || 'No data'}</p>
    </Card>
  );

  const { monte_carlo, lstm_forecast, risk_metrics } = {
    monte_carlo: sim.monte_carlo || {},
    lstm_forecast: sim.lstm_forecast || {},
    risk_metrics: sim.monte_carlo?.risk_metrics || {},
  };

  const fanChart = monte_carlo.fan_chart || [];
  const distChart = monte_carlo.distribution_chart || [];
  const termStats = monte_carlo.terminal_stats || {};
  const probProfit = risk_metrics.probability_of_profit_pct || 0;

  // Badge color based on expected return
  const expReturn = risk_metrics.expected_return_pct || 0;
  const badgeColor = expReturn > 10 ? 'bg-emerald-500/20 text-emerald-400' :
                     expReturn > 0 ? 'bg-cyan-500/20 text-cyan-400' :
                     'bg-red-500/20 text-red-400';

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4 relative overflow-hidden" data-testid={`simulation-${strategyType}`}>
      {/* Subtle corner glow */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-cyan-500/5 to-transparent pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between mb-3 relative">
        <div>
          <div className="flex items-center gap-1.5">
            <Brain className="w-3.5 h-3.5 text-cyan-400" />
            <p className="text-xs font-semibold text-[hsl(var(--foreground))]">{sim.strategy}</p>
          </div>
          <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">
            {lstm_forecast.method === 'lstm' ? 'LSTM' : 'Historical'} calibrated | {sim.stocks_simulated} stocks | 10K paths
          </p>
        </div>
        <div className="text-right">
          <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${badgeColor}`} data-testid={`simulation-expected-return-${strategyType}`}>
            E[R]: {expReturn >= 0 ? '+' : ''}{expReturn}%
          </span>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] mt-1">
            {probProfit}% prob profit
          </p>
        </div>
      </div>

      {/* Fan Chart — Monte Carlo Confidence Bands */}
      {fanChart.length > 2 && (
        <div className="mb-3" data-testid={`simulation-fan-chart-${strategyType}`}>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] mb-1 uppercase tracking-wider">1-Year Forward Projection (₹)</p>
          <ResponsiveContainer width="100%" height={160}>
            <ComposedChart data={fanChart} margin={{ top: 5, right: 5, bottom: 5, left: -5 }}>
              <defs>
                <linearGradient id={`fan-outer-${strategyType}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.08} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id={`fan-inner-${strategyType}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 14% 14%)" />
              <XAxis dataKey="week" tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `W${v}`} interval={Math.max(1, Math.floor(fanChart.length / 8))} />
              <YAxis tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${(v / 1e5).toFixed(1)}L`} domain={['dataMin', 'dataMax']} />
              <Tooltip
                contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
                formatter={(val, name) => {
                  const labels = { p5: '5th pct', p25: '25th pct', p50: 'Median', p75: '75th pct', p95: '95th pct', mean: 'Mean' };
                  return [`₹${(val / 1e5).toFixed(2)}L`, labels[name] || name];
                }}
              />
              {/* P5-P95 outer band */}
              <Area type="monotone" dataKey="p95" stroke="none" fill={`url(#fan-outer-${strategyType})`} />
              <Area type="monotone" dataKey="p5" stroke="none" fill="hsl(222 18% 8%)" />
              {/* P25-P75 inner band */}
              <Area type="monotone" dataKey="p75" stroke="none" fill={`url(#fan-inner-${strategyType})`} />
              <Area type="monotone" dataKey="p25" stroke="none" fill="hsl(222 18% 8%)" />
              {/* Median line */}
              <Line type="monotone" dataKey="p50" stroke="#06b6d4" strokeWidth={2} dot={false} name="p50" />
              {/* Mean line */}
              <Line type="monotone" dataKey="mean" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4 4" dot={false} name="mean" />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="flex items-center gap-3 mt-1 justify-center">
            <div className="flex items-center gap-1"><div className="w-6 h-[2px] bg-cyan-400" /><span className="text-[9px] text-[hsl(var(--muted-foreground))]">Median</span></div>
            <div className="flex items-center gap-1"><div className="w-6 h-[2px] bg-amber-400 border-dashed" style={{ borderBottom: '1px dashed #f59e0b', height: 0 }} /><span className="text-[9px] text-[hsl(var(--muted-foreground))]">Mean</span></div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-cyan-400/15" /><span className="text-[9px] text-[hsl(var(--muted-foreground))]">25-75th</span></div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-cyan-400/5" /><span className="text-[9px] text-[hsl(var(--muted-foreground))]">5-95th</span></div>
          </div>
        </div>
      )}

      {/* Return Distribution Histogram */}
      {distChart.length > 2 && (
        <div className="mb-3" data-testid={`simulation-distribution-${strategyType}`}>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] mb-1 uppercase tracking-wider">Terminal Return Distribution</p>
          <ResponsiveContainer width="100%" height={80}>
            <BarChart data={distChart} margin={{ top: 2, right: 5, bottom: 2, left: -15 }}>
              <XAxis dataKey="return_pct" tick={{ fontSize: 7, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} interval={Math.floor(distChart.length / 5)} />
              <YAxis tick={false} width={10} />
              <Tooltip
                contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
                formatter={(val, name) => [val, 'Paths']}
                labelFormatter={v => `Return: ${v}%`}
              />
              <ReferenceLine x={0} stroke="hsl(215 16% 50%)" strokeDasharray="2 2" />
              <Bar dataKey="frequency" name="Paths">
                {distChart.map((entry, i) => (
                  <Cell key={i} fill={entry.return_pct >= 0 ? 'hsla(186,92%,42%,0.6)' : 'hsla(0,72%,52%,0.5)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Risk Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-3 gap-y-2 mt-2" data-testid={`simulation-metrics-${strategyType}`}>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">VaR (95%)</p>
          <p className="text-xs font-mono font-bold text-red-400">{risk_metrics.var_95_pct}%</p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">CVaR (95%)</p>
          <p className="text-xs font-mono font-bold text-red-400">{risk_metrics.cvar_95_pct}%</p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Max Exp DD</p>
          <p className="text-xs font-mono font-bold text-red-400">-{risk_metrics.max_expected_drawdown_pct}%</p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Median Return</p>
          <p className={`text-xs font-mono font-bold ${(risk_metrics.median_return_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {(risk_metrics.median_return_pct || 0) >= 0 ? '+' : ''}{risk_metrics.median_return_pct}%
          </p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Range (25-75)</p>
          <p className="text-xs font-mono font-bold text-[hsl(var(--foreground))]">
            {risk_metrics.return_range_25_75?.[0]}% to {risk_metrics.return_range_25_75?.[1]}%
          </p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">P(Profit)</p>
          <p className={`text-xs font-mono font-bold ${probProfit >= 60 ? 'text-emerald-400' : probProfit >= 45 ? 'text-amber-400' : 'text-red-400'}`}>
            {probProfit}%
          </p>
        </div>
      </div>

      {/* Terminal Value Summary */}
      <div className="mt-3 pt-2 border-t border-[hsl(var(--border))]/50">
        <div className="flex items-center justify-between text-[9px] text-[hsl(var(--muted-foreground))]">
          <span>Worst: ₹{(termStats.worst_case_value / 1e5).toFixed(1)}L</span>
          <span className="text-cyan-400 font-mono font-semibold">Median: ₹{(termStats.median_value / 1e5).toFixed(1)}L</span>
          <span>Best: ₹{(termStats.best_case_value / 1e5).toFixed(1)}L</span>
        </div>
        <div className="flex items-center justify-between mt-1 text-[9px] text-[hsl(var(--muted-foreground))]">
          <span>LSTM vol: {lstm_forecast.annualized_volatility_pct}%</span>
          <span>{sim.computation_time_sec}s compute</span>
        </div>
      </div>
    </Card>
  );
}

function BacktestCard({ strategyType, strategyName }) {
  const [bt, setBt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState(null);

  const fetchBacktest = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portfolios/backtest/${strategyType}`);
      const d = await res.json();
      if (d.status === 'computing') {
        setComputing(true);
        setLoading(false);
        return false;
      }
      if (d.error) {
        setError(d.error);
        setComputing(false);
        setLoading(false);
        return true;
      }
      setBt(d);
      setComputing(false);
      setLoading(false);
      return true;
    } catch (e) {
      setError('Failed to load backtest');
      setComputing(false);
      setLoading(false);
      return true;
    }
  }, [strategyType]);

  useEffect(() => {
    setLoading(true);
    fetchBacktest();
  }, [fetchBacktest]);

  useEffect(() => {
    if (!computing) return;
    const interval = setInterval(async () => {
      const done = await fetchBacktest();
      if (done) clearInterval(interval);
    }, 10000);
    return () => clearInterval(interval);
  }, [computing, fetchBacktest]);

  if (loading || computing) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--primary))]" />
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          {computing ? 'Computing 5Y backtest...' : `Loading backtest for ${strategyName}...`}
        </span>
      </div>
      {computing && <p className="text-[9px] text-[hsl(var(--muted-foreground))] mt-2">Auto-refreshing every 10s</p>}
    </Card>
  );

  if (error || !bt) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
      <p className="text-xs text-[hsl(var(--muted-foreground))]">{strategyName}: {error || 'No data'}</p>
    </Card>
  );

  const isAlpha = bt.alpha_pct > 0;

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid={`backtest-${strategyType}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-xs font-semibold text-[hsl(var(--foreground))]">{bt.strategy}</p>
          <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{bt.years}Y lookback | {bt.stocks_tested} stocks | {bt.months} months</p>
        </div>
        <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${isAlpha ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
          Alpha: {bt.alpha_pct >= 0 ? '+' : ''}{bt.alpha_pct}%
        </span>
      </div>

      {/* Cumulative return chart */}
      {bt.chart_data && bt.chart_data.length > 2 && (
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={bt.chart_data} margin={{ top: 5, right: 5, bottom: 5, left: -15 }}>
            <defs>
              <linearGradient id={`grad-${strategyType}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.15}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 14% 14%)" />
            <XAxis dataKey="month" tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `M${v}`} interval={Math.floor((bt.chart_data?.length || 12) / 6)} />
            <YAxis tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} />
            <Tooltip
              contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
              formatter={(val, name) => [`${val}%`, name === 'portfolio' ? 'Strategy' : 'Nifty 50']}
            />
            <Area type="monotone" dataKey="portfolio" stroke="#10b981" fill={`url(#grad-${strategyType})`} strokeWidth={1.5} name="portfolio" />
            {bt.chart_data[0]?.nifty50 !== undefined && (
              <Line type="monotone" dataKey="nifty50" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4 4" dot={false} name="nifty50" />
            )}
          </AreaChart>
        </ResponsiveContainer>
      )}

      {/* Metrics grid */}
      <div className="grid grid-cols-4 gap-2 mt-3">
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">CAGR</p>
          <p className={`text-xs font-mono font-bold ${bt.cagr_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {bt.cagr_pct >= 0 ? '+' : ''}{bt.cagr_pct}%
          </p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Max DD</p>
          <p className="text-xs font-mono font-bold text-red-400">-{bt.max_drawdown_pct}%</p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Sharpe</p>
          <p className={`text-xs font-mono font-bold ${bt.sharpe_ratio >= 1 ? 'text-emerald-400' : bt.sharpe_ratio >= 0.5 ? 'text-amber-400' : 'text-red-400'}`}>
            {bt.sharpe_ratio}
          </p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Win Rate</p>
          <p className="text-xs font-mono font-bold text-[hsl(var(--foreground))]">{bt.win_rate_monthly_pct}%</p>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 mt-1">
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Total</p>
          <p className={`text-xs font-mono ${bt.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {bt.total_return_pct >= 0 ? '+' : ''}{bt.total_return_pct}%
          </p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Nifty 50</p>
          <p className="text-xs font-mono text-amber-400">{bt.benchmark_total_return_pct >= 0 ? '+' : ''}{bt.benchmark_total_return_pct}%</p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Volatility</p>
          <p className="text-xs font-mono text-[hsl(var(--foreground))]">{bt.annual_volatility_pct}%</p>
        </div>
        <div>
          <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Best Mo</p>
          <p className="text-xs font-mono text-emerald-400">+{bt.best_month_pct}%</p>
        </div>
      </div>
    </Card>
  );
}

function WalkForwardSection({ portfolios }) {
  const [wfData, setWfData] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const results = {};
      for (const p of portfolios) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/portfolios/walk-forward/${p.type}`);
          const d = await res.json();
          if (d.records && d.records.length > 0) {
            results[p.type] = d.records;
          }
        } catch (e) { /* skip */ }
      }
      setWfData(results);
      setLoading(false);
    }
    if (portfolios?.length) load();
  }, [portfolios]);

  if (loading) return null;
  const hasData = Object.keys(wfData).length > 0;
  if (!hasData) return null;

  return (
    <div data-testid="walk-forward-section">
      <div className="flex items-center gap-2 mb-1">
        <Crosshair className="w-4 h-4 text-amber-400" />
        <h2 className="text-base font-display font-bold text-[hsl(var(--foreground))]">Walk-Forward Tracking</h2>
        <span className="text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded font-mono">
          Forecast vs Actual
        </span>
      </div>
      <p className="text-[11px] text-[hsl(var(--muted-foreground))] mb-4 ml-6">
        Tracking simulation predictions against actual portfolio performance over time
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {portfolios.map(p => {
          const records = wfData[p.type];
          if (!records || records.length === 0) return null;
          const latest = records[records.length - 1];
          const forecast = latest.forecast || {};
          const actual = latest.actual || {};
          const deviation = forecast.expected_return_pct - (actual.total_pnl_pct || 0);

          return (
            <Card key={p.type} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid={`walk-forward-${p.type}`}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-[hsl(var(--foreground))]">{p.name}</p>
                <span className="text-[9px] text-[hsl(var(--muted-foreground))] font-mono">{records.length} snapshots</span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="bg-cyan-500/5 rounded-lg p-2 border border-cyan-500/10">
                  <p className="text-[9px] text-cyan-400 uppercase tracking-wider mb-1">Forecast (MC)</p>
                  <p className="text-sm font-mono font-bold text-cyan-400">
                    {forecast.expected_return_pct >= 0 ? '+' : ''}{forecast.expected_return_pct?.toFixed(1)}%
                  </p>
                  <p className="text-[9px] text-[hsl(var(--muted-foreground))] mt-0.5">
                    P(Profit): {forecast.probability_of_profit_pct?.toFixed(0)}%
                  </p>
                </div>
                <div className="bg-emerald-500/5 rounded-lg p-2 border border-emerald-500/10">
                  <p className="text-[9px] text-emerald-400 uppercase tracking-wider mb-1">Actual (Live)</p>
                  <p className={`text-sm font-mono font-bold ${(actual.total_pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(actual.total_pnl_pct || 0) >= 0 ? '+' : ''}{(actual.total_pnl_pct || 0).toFixed(2)}%
                  </p>
                  <p className="text-[9px] text-[hsl(var(--muted-foreground))] mt-0.5">
                    Value: {actual.portfolio_value ? `₹${(actual.portfolio_value / 1e5).toFixed(1)}L` : '--'}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))]/50">
                <div>
                  <p className="text-[9px] text-[hsl(var(--muted-foreground))]">Deviation</p>
                  <p className={`text-xs font-mono font-bold ${Math.abs(deviation) < 10 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {deviation >= 0 ? '+' : ''}{deviation.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-[9px] text-[hsl(var(--muted-foreground))]">LSTM Vol</p>
                  <p className="text-xs font-mono text-[hsl(var(--foreground))]">{forecast.lstm_annualized_vol_pct?.toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-[9px] text-[hsl(var(--muted-foreground))]">VaR 95%</p>
                  <p className="text-xs font-mono text-red-400">{forecast.var_95_pct?.toFixed(1)}%</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default function PortfolioAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portfolios/analytics`);
      const d = await res.json();
      setData(d);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const handleRebuild = async () => {
    if (!window.confirm('This will delete all 6 portfolios and reconstruct them with the hardened v3 pipeline. Backtests and simulations will be cleared. Continue?')) return;
    setRebuilding(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/portfolios/rebuild-all`, { method: 'POST' });
      const d = await res.json();
      alert(`${d.message}\n\nCleared: ${d.cleared_caches?.portfolios || 0} portfolios, ${d.cleared_caches?.backtests || 0} backtests, ${d.cleared_caches?.simulations || 0} simulations`);
      await fetchData();
    } catch (e) {
      alert('Rebuild failed: ' + e.message);
    }
    setRebuilding(false);
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64" data-testid="analytics-loading">
        <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (!data || data.error || !data.portfolios?.length) {
    return (
      <div className="p-6 text-center" data-testid="analytics-empty">
        <Activity className="w-8 h-8 text-[hsl(var(--muted-foreground))] mx-auto mb-2" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {data?.error || 'Portfolios are being constructed by God Mode AI with hardened v3 pipeline. This takes ~5-10 min per portfolio.'}
        </p>
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2">Auto-refreshing every 60s. The daemon constructs them one by one.</p>
      </div>
    );
  }

  const { portfolios, global_sector_allocation, total_invested, total_value, total_pnl, total_pnl_pct, aggregate_beta, active_count } = data;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-[1920px]" data-testid="analytics-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-display font-bold text-[hsl(var(--foreground))]" data-testid="analytics-title">
            Portfolio Analytics
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            Sector allocation, risk metrics, performance comparison across {active_count} AI strategies
          </p>
        </div>
        <div className="flex items-center gap-2">
          {(getUser()?.superadmin || getUser()?.sub === 'somnath.dey@smifs.com') && (
            <button onClick={handleRebuild} disabled={rebuilding}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 disabled:opacity-50"
              data-testid="rebuild-portfolios-btn">
              <RotateCcw className={`w-4 h-4 ${rebuilding ? 'animate-spin' : ''}`} />
              Rebuild v3
            </button>
          )}
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50"
            data-testid="refresh-analytics-btn">
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Aggregate Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="aggregate-metrics">
        <MetricCard label="Total Invested" value={`${(total_invested / 1e5).toFixed(0)}L`} icon={BarChart3} />
        <MetricCard label="Current Value" value={`${(total_value / 1e5).toFixed(1)}L`} icon={TrendingUp} />
        <MetricCard
          label="Total Return"
          value={`${total_pnl_pct >= 0 ? '+' : ''}${total_pnl_pct.toFixed(2)}%`}
          color={total_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
          icon={total_pnl_pct >= 0 ? TrendingUp : TrendingDown}
        />
        <MetricCard
          label="Total P&L"
          value={`${total_pnl >= 0 ? '+' : ''}${(total_pnl / 1e5).toFixed(2)}L`}
          color={total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}
          icon={Activity}
        />
        <MetricCard label="Avg Beta" value={aggregate_beta ?? '—'} icon={Shield} />
        <MetricCard label="Active Strategies" value={`${active_count}/6`} icon={Award} color="text-emerald-400" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4 lg:col-span-1">
          <SectorPieChart data={global_sector_allocation} title="Global Sector Allocation" />
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4 lg:col-span-1">
          <PerformanceComparison portfolios={portfolios} />
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4 lg:col-span-1">
          <RiskRadar portfolios={portfolios} />
        </Card>
      </div>

      {/* Risk Metrics Table */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
        <PortfolioRiskTable portfolios={portfolios} />
      </Card>

      {/* Per-Portfolio Sector Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="per-portfolio-sectors">
        {portfolios.map(p => (
          <Card key={p.type} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
            <SectorPieChart data={p.sector_allocation} title={p.name} />
          </Card>
        ))}
      </div>

      {/* 5-Year Backtest Results */}
      <div data-testid="backtest-section">
        <div className="flex items-center gap-2 mb-4">
          <History className="w-4 h-4 text-[hsl(var(--primary))]" />
          <h2 className="text-base font-display font-bold text-[hsl(var(--foreground))]">5-Year Backtest Evidence</h2>
          <span className="text-[10px] bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] px-2 py-0.5 rounded">
            Lookback analysis vs Nifty 50 benchmark
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {portfolios.map(p => (
            <BacktestCard key={p.type} strategyType={p.type} strategyName={p.name} />
          ))}
        </div>
      </div>

      {/* LSTM + Monte Carlo Forward Simulation */}
      <div data-testid="simulation-section">
        <div className="flex items-center gap-2 mb-1">
          <Brain className="w-4 h-4 text-cyan-400" />
          <h2 className="text-base font-display font-bold text-[hsl(var(--foreground))]">Forward Simulation Engine</h2>
          <span className="text-[10px] bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded font-mono">
            LSTM + Monte Carlo
          </span>
        </div>
        <p className="text-[11px] text-[hsl(var(--muted-foreground))] mb-4 ml-6">
          Neural network calibrated 10,000-path GBM simulation | 1-year horizon | VaR, CVaR, probability of profit
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {portfolios.map(p => (
            <SimulationCard key={p.type} strategyType={p.type} strategyName={p.name} />
          ))}
        </div>
      </div>

      {/* Walk-Forward Tracking */}
      <WalkForwardSection portfolios={portfolios} />
    </div>
  );
}

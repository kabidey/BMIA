import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, BarChart3, PieChart as PieChartIcon, TrendingUp, TrendingDown, Shield, Activity, Award, AlertTriangle, Loader2 } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend } from 'recharts';

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

export default function PortfolioAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

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
          {data?.error || 'Portfolios are being constructed by God Mode AI. Check back shortly.'}
        </p>
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
        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50"
          data-testid="refresh-analytics-btn">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
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
    </div>
  );
}

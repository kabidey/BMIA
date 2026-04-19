import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Skeleton } from '../components/ui/skeleton';
import {
  Globe2, TrendingUp, TrendingDown, RefreshCw, BarChart3, Gem,
  DollarSign, Landmark, ArrowUpRight, ArrowDownRight, Minus, Search,
  Activity, Layers, ArrowLeft, LineChart, ChevronRight, Newspaper,
  Calendar, Users, Scale, Target, ExternalLink
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart as RLineChart, Line, XAxis, YAxis,
  Tooltip, BarChart, Bar, Cell, CartesianGrid, ScatterChart, Scatter, ZAxis
} from 'recharts';
import MarketIntel from '../components/MarketIntel';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// ── Helpers ────────────────────────────────────────────────────────
function fmt(v, dec = 2) {
  if (v === null || v === undefined) return '-';
  return Number(v).toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function fmtLarge(v) {
  if (!v) return '-';
  const n = Number(v);
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e7) return `${(n / 1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `${(n / 1e5).toFixed(2)}L`;
  return fmt(n, 0);
}
function color(v) {
  if (v === null || v === undefined) return 'text-[hsl(var(--muted-foreground))]';
  return v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-[hsl(var(--muted-foreground))]';
}
function arrow(v) {
  if (v > 0) return <ArrowUpRight className="w-3 h-3 text-emerald-400 inline" />;
  if (v < 0) return <ArrowDownRight className="w-3 h-3 text-red-400 inline" />;
  return <Minus className="w-3 h-3 text-[hsl(var(--muted-foreground))] inline" />;
}
function RangeBar({ low, high, current }) {
  if (!low || !high || !current) return <span className="text-[10px] text-[hsl(var(--muted-foreground))]">-</span>;
  const pct = Math.min(100, Math.max(0, ((current - low) / (high - low)) * 100));
  return (
    <div className="flex items-center gap-1.5 min-w-[100px]">
      <span className="text-[9px] font-mono text-[hsl(var(--muted-foreground))]">{fmt(low, 0)}</span>
      <div className="flex-1 h-1 bg-[hsl(var(--border))] rounded-full relative">
        <div className="absolute h-1 bg-[hsl(var(--primary))] rounded-full" style={{ width: `${pct}%` }} />
        <div className="absolute w-2 h-2 bg-[hsl(var(--primary))] rounded-full -top-0.5" style={{ left: `${pct}%`, transform: 'translateX(-50%)' }} />
      </div>
      <span className="text-[9px] font-mono text-[hsl(var(--muted-foreground))]">{fmt(high, 0)}</span>
    </div>
  );
}

// ── Market Data Table ──────────────────────────────────────────────
function MarketTable({ data, title, icon: Icon, iconColor, onRowClick, compact = false }) {
  if (!data || data.length === 0) return null;
  return (
    <div data-testid={`table-${title.replace(/\s+/g, '-').toLowerCase()}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${iconColor}`} />
        <h3 className="text-sm font-display font-semibold">{title}</h3>
        <Badge variant="outline" className="text-[9px] font-mono">{data.length}</Badge>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[hsl(var(--border))]/50 text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
              <th className="text-left py-1.5 pr-2">Name</th>
              <th className="text-right px-1">Price</th>
              <th className="text-right px-1">Chg</th>
              <th className="text-right px-1">%</th>
              <th className="text-right px-1 hidden sm:table-cell">Z</th>
              {!compact && <th className="text-right px-1 hidden md:table-cell">1Y%</th>}
              {!compact && <th className="text-right px-1 hidden md:table-cell">YTD%</th>}
              {!compact && <th className="text-center px-1 hidden lg:table-cell">52W Range</th>}
              {!compact && <th className="text-right px-1 hidden lg:table-cell">Vol</th>}
            </tr>
          </thead>
          <tbody>
            {data.map((d, i) => (
              <tr key={d.symbol || i}
                className="border-b border-[hsl(var(--border))]/20 hover:bg-[hsl(var(--surface-2))] cursor-pointer transition-colors"
                onClick={() => onRowClick?.(d.symbol)}
                data-testid={`row-${d.symbol}`}>
                <td className="py-1.5 pr-2">
                  <div className="flex items-center gap-1.5">
                    {arrow(d.change_pct)}
                    <span className="font-medium text-[hsl(var(--foreground))] truncate max-w-[120px] sm:max-w-[180px]">{d.name}</span>
                    <span className="text-[9px] text-[hsl(var(--muted-foreground))] font-mono hidden sm:inline">{d.symbol?.replace('=F', '').replace('=X', '')}</span>
                  </div>
                </td>
                <td className="text-right px-1 font-mono font-medium">{fmt(d.price)}</td>
                <td className={`text-right px-1 font-mono ${color(d.change)}`}>{d.change > 0 ? '+' : ''}{fmt(d.change)}</td>
                <td className={`text-right px-1 font-mono font-bold ${color(d.change_pct)}`}>{d.change_pct > 0 ? '+' : ''}{fmt(d.change_pct)}%</td>
                <td className={`text-right px-1 font-mono hidden sm:table-cell ${color(d.z_score)}`}>{d.z_score !== null ? fmt(d.z_score, 1) : '-'}</td>
                {!compact && <td className={`text-right px-1 font-mono hidden md:table-cell ${color(d.ret_1y)}`}>{d.ret_1y !== null ? `${d.ret_1y > 0 ? '+' : ''}${fmt(d.ret_1y)}%` : '-'}</td>}
                {!compact && <td className={`text-right px-1 font-mono hidden md:table-cell ${color(d.ret_ytd)}`}>{d.ret_ytd !== null ? `${d.ret_ytd > 0 ? '+' : ''}${fmt(d.ret_ytd)}%` : '-'}</td>}
                {!compact && <td className="px-1 hidden lg:table-cell"><RangeBar low={d.low_52w} high={d.high_52w} current={d.price} /></td>}
                {!compact && <td className="text-right px-1 font-mono hidden lg:table-cell text-[10px]">{d.volume ? fmtLarge(d.volume) : '-'}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Factor Grid ────────────────────────────────────────────────────
function FactorGrid({ grid }) {
  if (!grid) return null;
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="factor-grid">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-display font-semibold">Indian Market Factor Grid</h3>
        <span className="text-[10px] text-[hsl(var(--muted-foreground))]">1-Day Performance</span>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">
            <th className="text-left py-1 w-16"></th>
            {grid.headers.map(h => <th key={h} className="text-center py-1 px-2">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map(row => (
            <tr key={row.label} className="border-t border-[hsl(var(--border))]/30">
              <td className="py-2 font-semibold text-[hsl(var(--muted-foreground))]">{row.label}</td>
              {row.cells.map((cell, i) => {
                const v = parseFloat(cell);
                const bg = !isNaN(v) ? (v > 0 ? 'bg-emerald-500/15' : v < 0 ? 'bg-red-500/15' : 'bg-[hsl(var(--surface-2))]') : 'bg-[hsl(var(--surface-2))]';
                const tc = !isNaN(v) ? (v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : '') : '';
                return <td key={i} className={`text-center py-2 px-2 font-mono font-bold ${bg} ${tc} rounded`}>{cell}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

// ── Performance Rankings Bar Chart ─────────────────────────────────
function PerfRankings({ rankings }) {
  if (!rankings || rankings.length === 0) return null;
  const chartData = rankings.slice(0, 15).map(r => ({
    name: r.name.length > 15 ? r.name.slice(0, 14) + '…' : r.name,
    ret: r.ret_1y,
  }));
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="perf-rankings">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-display font-semibold">1-Year Performance Rankings</h3>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 80, right: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
          <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: 'hsl(var(--foreground))', fontSize: 10 }} width={80} />
          <Tooltip formatter={(v) => [`${v}%`, '1Y Return']} contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 11 }} />
          <Bar dataKey="ret" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.ret >= 0 ? '#34d399' : '#f87171'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

// ── Stock Snapshot Page ────────────────────────────────────────────
function StockSnapshot({ symbol, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chartPeriod, setChartPeriod] = useState('3M');

  useEffect(() => {
    setLoading(true);
    fetch(`${BACKEND_URL}/api/big-market/snapshot/${encodeURIComponent(symbol)}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  if (loading) return (
    <div className="p-4 space-y-4">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-64 w-full" />
      <div className="grid grid-cols-2 gap-4"><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
    </div>
  );
  if (!data) return <div className="p-8 text-center text-[hsl(var(--muted-foreground))]">No data for {symbol}</div>;

  const periods = { MTD: 21, '1M': 21, QTD: 63, '3M': 63, '6M': 126, YTD: 180, '1Y': 252, ALL: 9999 };
  const chartSlice = data.chart_data?.slice(-(periods[chartPeriod] || 63)) || [];
  const isPositive = data.change >= 0;

  return (
    <div className="space-y-5" data-testid="stock-snapshot">
      {/* Header */}
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Big Market
        </button>
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-display font-bold">{data.name}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <Badge variant="outline" className="font-mono text-xs">{symbol}</Badge>
              <Badge variant="outline" className="text-[10px]">{data.exchange}</Badge>
              <span className={`text-lg font-mono font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                {fmt(data.price)} <span className="text-sm">{data.currency}</span>
              </span>
              <span className={`text-sm font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{fmt(data.change)} ({isPositive ? '+' : ''}{fmt(data.change_pct)}%)
              </span>
            </div>
          </div>
          {/* Quick KPIs */}
          <div className="flex gap-3 flex-wrap text-xs">
            {[
              { l: 'P/E', v: data.valuation?.pe_trailing },
              { l: 'P/B', v: data.valuation?.pb },
              { l: 'EV/EBITDA', v: data.valuation?.ev_ebitda },
              { l: 'Fwd P/E', v: data.valuation?.pe_forward },
            ].map(k => (
              <div key={k.l} className="text-center">
                <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{k.l}</p>
                <p className="font-mono font-bold">{k.v ? `${k.v}x` : '-'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chart + Key Data */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Snapshot Chart */}
        <Card className="lg:col-span-3 bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <h3 className="text-sm font-semibold">Snapshot Chart</h3>
            <div className="flex gap-0.5 ml-auto">
              {Object.keys(periods).map(p => (
                <button key={p} onClick={() => setChartPeriod(p)}
                  className={`px-2 py-0.5 text-[10px] font-mono rounded ${chartPeriod === p ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]' : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]'}`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <RLineChart data={chartSlice}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.2} />
              <XAxis dataKey="date" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 9 }} tickFormatter={d => d?.slice(5)} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 9 }} tickFormatter={v => fmt(v, 0)} />
              <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 11 }} />
              <Line type="monotone" dataKey="close" stroke={isPositive ? '#34d399' : '#f87171'} strokeWidth={2} dot={false} />
            </RLineChart>
          </ResponsiveContainer>
        </Card>

        {/* Key Data + Valuation */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
            <h3 className="text-sm font-semibold mb-2">Key Data</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              {[
                ['Dividend Yield', data.key_data?.dividend_yield ? `${data.key_data.dividend_yield}%` : '-'],
                ['Avg Vol (10D)', data.key_data?.avg_volume_10d ? fmtLarge(data.key_data.avg_volume_10d) : '-'],
                ['Beta (5Y)', data.key_data?.beta ?? '-'],
                ['Volatility (1Y)', data.key_data?.volatility_1y ?? '-'],
                ['Shares Out', data.key_data?.shares_outstanding ? fmtLarge(data.key_data.shares_outstanding) : '-'],
                ['Short Interest', data.key_data?.short_interest_pct ? `${data.key_data.short_interest_pct}%` : '-'],
                ['Industry', data.key_data?.industry || '-'],
                ['Sector', data.key_data?.sector || '-'],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between border-b border-[hsl(var(--border))]/20 py-1">
                  <span className="text-[hsl(var(--muted-foreground))]">{l}</span>
                  <span className="font-mono font-medium text-right">{v}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Performance Returns */}
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
            <h3 className="text-sm font-semibold mb-2">Performance Returns</h3>
            <table className="w-full text-xs">
              <thead><tr className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">
                <th className="text-left"></th><th className="text-right">1M</th><th className="text-right">3M</th><th className="text-right">YTD</th><th className="text-right">1Y</th>
              </tr></thead>
              <tbody><tr className="font-mono">
                <td className="py-1 text-[hsl(var(--muted-foreground))]">Price</td>
                {['ret_1m', 'ret_3m', 'ret_ytd', 'ret_1y'].map(k => {
                  const v = data.performance?.[k];
                  return <td key={k} className={`text-right font-bold ${color(v)}`}>{v !== null && v !== undefined ? `${v > 0 ? '+' : ''}${v}%` : '-'}</td>;
                })}
              </tr></tbody>
            </table>
          </Card>
        </div>
      </div>

      {/* Valuation + Capital Structure */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
          <h3 className="text-sm font-semibold mb-2">Valuation</h3>
          <table className="w-full text-xs">
            <thead><tr className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">
              <th className="text-left"></th><th className="text-right">LTM</th><th className="text-right">NTM</th>
            </tr></thead>
            <tbody>
              {[
                ['P/E', data.valuation?.pe_trailing, data.valuation?.pe_forward],
                ['EV/Sales', data.valuation?.ev_sales, null],
                ['EV/EBITDA', data.valuation?.ev_ebitda, null],
                ['Price/Book', data.valuation?.pb, null],
              ].map(([l, ltm, ntm]) => (
                <tr key={l} className="border-t border-[hsl(var(--border))]/20">
                  <td className="py-1.5 text-[hsl(var(--muted-foreground))]">{l}</td>
                  <td className="text-right font-mono font-bold">{ltm ? `${ltm}x` : '-'}</td>
                  <td className="text-right font-mono font-bold">{ntm ? `${ntm}x` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
          <h3 className="text-sm font-semibold mb-2">Capital Structure</h3>
          <div className="space-y-1.5 text-xs">
            {[
              ['Market Cap', data.capital_structure?.market_cap],
              ['Total Debt', data.capital_structure?.total_debt],
              ['Cash & Inv.', data.capital_structure?.cash],
              ['Enterprise Value', data.capital_structure?.enterprise_value],
            ].map(([l, v]) => (
              <div key={l} className="flex justify-between border-b border-[hsl(var(--border))]/20 py-1">
                <span className="text-[hsl(var(--muted-foreground))]">{l}</span>
                <span className="font-mono font-bold">{v ? `Rs ${fmtLarge(v)}` : '-'}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════
// MAIN: BIG MARKET PAGE
// ══════════════════════════════════════════════════════════════════════
export default function BigMarket() {
  const { symbol: routeSymbol } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedStock, setSelectedStock] = useState(routeSymbol || null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/big-market/overview`);
      if (res.ok) setData(await res.json());
    } catch { /* */ }
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRefresh = () => { setRefreshing(true); fetchData(); };

  const handleRowClick = (sym) => {
    setSelectedStock(sym);
    navigate(`/big-market/snapshot/${encodeURIComponent(sym)}`);
  };

  // If viewing a stock snapshot
  if (selectedStock) {
    return (
      <div className="p-4 sm:p-6 max-w-[1920px] mx-auto">
        <StockSnapshot symbol={selectedStock} onBack={() => { setSelectedStock(null); navigate('/big-market'); }} />
      </div>
    );
  }

  if (loading) return (
    <div className="p-4 sm:p-6 space-y-6 max-w-[1920px] mx-auto">
      <div className="flex items-center gap-3"><Skeleton className="h-8 w-48" /><Skeleton className="h-6 w-20" /></div>
      {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-48 w-full" />)}
    </div>
  );

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-[1920px] mx-auto" data-testid="big-market-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Globe2 className="w-7 h-7 text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl sm:text-2xl font-display font-bold">Big Market</h1>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Global markets, Indian indices, commodities, currencies, yields
              {data?.fetched_at && ` — ${new Date(data.fetched_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Quick stock search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />
            <input type="text" placeholder="Search ticker..." value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && searchTerm.trim()) handleRowClick(searchTerm.trim().toUpperCase() + (searchTerm.includes('.') ? '' : '.NS')); }}
              className="pl-8 pr-3 py-1.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-xs w-40 sm:w-56"
              data-testid="big-market-search" />
          </div>
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-xs hover:bg-[hsl(var(--primary))]/10"
            data-testid="big-market-refresh">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Tabbed sections */}
      <Tabs defaultValue="india" className="w-full" data-testid="big-market-tabs">
        <TabsList className="w-full flex flex-wrap h-auto gap-1 bg-[hsl(var(--surface-2))] p-1 rounded-lg">
          <TabsTrigger value="india" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md"><Activity className="w-3 h-3" />India</TabsTrigger>
          <TabsTrigger value="global" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md"><Globe2 className="w-3 h-3" />Global</TabsTrigger>
          <TabsTrigger value="commodities" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md"><Gem className="w-3 h-3" />Commodities</TabsTrigger>
          <TabsTrigger value="currencies" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md"><DollarSign className="w-3 h-3" />Currencies</TabsTrigger>
          <TabsTrigger value="yields" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md"><Landmark className="w-3 h-3" />Yields</TabsTrigger>
          <TabsTrigger value="analysis" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md"><LineChart className="w-3 h-3" />Analysis</TabsTrigger>
          <TabsTrigger value="intel" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md" data-testid="intel-tab"><Newspaper className="w-3 h-3" />Intel</TabsTrigger>
        </TabsList>

        {/* India Tab */}
        <TabsContent value="india" className="mt-4 space-y-5">
          <MarketTable data={data?.indian_indices} title="Indian Indices" icon={Activity} iconColor="text-emerald-400" onRowClick={handleRowClick} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <FactorGrid grid={data?.factor_grid} />
            {data?.market_breadth && (
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="market-breadth">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-display font-semibold">Market Pulse</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 text-center">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Nifty 50</p>
                    <p className={`text-2xl font-mono font-bold ${color(data.market_breadth.nifty_chg_pct)}`}>
                      {data.market_breadth.nifty_chg_pct > 0 ? '+' : ''}{data.market_breadth.nifty_chg_pct}%
                    </p>
                  </div>
                  <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 text-center">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">India VIX</p>
                    <p className={`text-2xl font-mono font-bold ${(data.market_breadth.india_vix || 0) > 20 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {data.market_breadth.india_vix ?? '-'}
                    </p>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Global Tab */}
        <TabsContent value="global" className="mt-4 space-y-5">
          <MarketTable data={data?.global_indices} title="World Equity Indices" icon={Globe2} iconColor="text-blue-400" onRowClick={handleRowClick} />
        </TabsContent>

        {/* Commodities Tab */}
        <TabsContent value="commodities" className="mt-4">
          <MarketTable data={data?.commodities} title="Commodities" icon={Gem} iconColor="text-amber-400" onRowClick={handleRowClick} />
        </TabsContent>

        {/* Currencies Tab */}
        <TabsContent value="currencies" className="mt-4">
          <MarketTable data={data?.currencies} title="Currencies & FX" icon={DollarSign} iconColor="text-green-400" onRowClick={handleRowClick} compact />
        </TabsContent>

        {/* Yields Tab */}
        <TabsContent value="yields" className="mt-4">
          <MarketTable data={data?.yields} title="Government Yields" icon={Landmark} iconColor="text-purple-400" onRowClick={handleRowClick} compact />
        </TabsContent>

        {/* Analysis Tab */}
        <TabsContent value="analysis" className="mt-4 space-y-5">
          <PerfRankings rankings={data?.perf_rankings} />
        </TabsContent>

        {/* Intel Tab — Movers · FII/DII · Earnings · PCR · Estimates · News */}
        <TabsContent value="intel" className="mt-4">
          <MarketIntel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

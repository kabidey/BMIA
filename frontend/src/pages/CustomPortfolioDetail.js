import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import {
  ArrowLeft, RefreshCw, Loader2, IndianRupee, ArrowUpRight, ArrowDownRight,
  History, Trash2, ArrowRightLeft, Search, Plus, X, Minus, Save, AlertTriangle,
  ChevronDown, ChevronRight, Brain
} from 'lucide-react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, CartesianGrid, XAxis, YAxis,
  Area, AreaChart, ComposedChart, Line, BarChart, Bar, ReferenceLine, Legend
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const SECTOR_COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16'];

function StockSearch({ onAdd, addedSymbols }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/symbols?q=${encodeURIComponent(query)}`);
        const d = await res.json();
        setResults((d.symbols || []).filter(s => !addedSymbols.has(s.symbol)).slice(0, 6));
      } catch { setResults([]); }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, addedSymbols]);

  return (
    <div className="relative">
      <div className="flex items-center gap-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2">
        <Search className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />
        <input type="text" value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Add stock..." className="flex-1 bg-transparent text-xs text-[hsl(var(--foreground))] outline-none placeholder:text-[hsl(var(--muted-foreground))]" />
      </div>
      {results.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg shadow-xl max-h-48 overflow-y-auto">
          {results.map(s => (
            <button key={s.symbol} onClick={() => { onAdd(s); setQuery(''); setResults([]); }}
              className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-[hsl(var(--surface-2))]">
              <span className="font-mono font-medium">{s.symbol.replace('.NS', '')}</span>
              <span className="text-[hsl(var(--muted-foreground))]">{s.name?.slice(0, 20)}</span>
              <Plus className="w-3.5 h-3.5 text-emerald-400" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CustomBacktest({ portfolioId }) {
  const [bt, setBt] = useState(null);
  const [computing, setComputing] = useState(false);

  const fetchBt = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/custom-portfolios/${portfolioId}/backtest`);
      const d = await res.json();
      if (d.status === 'computing') { setComputing(true); return false; }
      if (!d.error && d.cagr_pct !== undefined) setBt(d);
      setComputing(false);
      return true;
    } catch { setComputing(false); return true; }
  }, [portfolioId]);

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
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="custom-backtest">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[hsl(var(--primary))]" />
          <p className="text-xs font-semibold text-[hsl(var(--foreground))]">5-Year Backtest</p>
          <span className="text-[9px] text-[hsl(var(--muted-foreground))]">{bt.years}Y | {bt.stocks_tested} stocks</span>
        </div>
        <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${isAlpha ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
          Alpha: {bt.alpha_pct >= 0 ? '+' : ''}{bt.alpha_pct}%
        </span>
      </div>
      {bt.chart_data?.length > 2 && (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={bt.chart_data} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
            <defs><linearGradient id="cbtGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.15} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 14% 14%)" />
            <XAxis dataKey="month" tick={{ fontSize: 9, fill: 'hsl(215 16% 70%)' }} interval={Math.floor(bt.chart_data.length / 8)} />
            <YAxis tick={{ fontSize: 9, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} />
            <Tooltip contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }} formatter={v => [`${v.toFixed(1)}%`]} />
            <Area type="monotone" dataKey="portfolio" stroke="#10b981" fill="url(#cbtGrad)" strokeWidth={2} name="Portfolio" />
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
          { l: 'Win Rate', v: `${bt.win_rate_monthly_pct}%`, c: 'text-[hsl(var(--foreground))]' },
          { l: 'Volatility', v: `${bt.annual_volatility_pct}%`, c: 'text-[hsl(var(--foreground))]' },
          { l: 'Nifty 50', v: `+${bt.benchmark_cagr_pct}%`, c: 'text-amber-400' },
        ].map(m => (<div key={m.l}><p className="text-[9px] text-[hsl(var(--muted-foreground))]">{m.l}</p><p className={`text-sm font-mono font-bold ${m.c}`}>{m.v}</p></div>))}
      </div>
    </Card>
  );
}

function CustomSimulation({ portfolioId }) {
  const [sim, setSim] = useState(null);
  const [computing, setComputing] = useState(false);

  const fetchSim = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/custom-portfolios/${portfolioId}/simulation`);
      const d = await res.json();
      if (d.status === 'computing') { setComputing(true); return false; }
      if (!d.error && d.monte_carlo) setSim(d);
      setComputing(false);
      return true;
    } catch { setComputing(false); return true; }
  }, [portfolioId]);

  useEffect(() => { fetchSim(); }, [fetchSim]);
  useEffect(() => {
    if (!computing) return;
    const iv = setInterval(async () => { if (await fetchSim()) clearInterval(iv); }, 15000);
    return () => clearInterval(iv);
  }, [computing, fetchSim]);

  if (!sim && !computing) return null;
  if (computing) return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
      <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-cyan-400" /><span className="text-xs text-[hsl(var(--muted-foreground))]">Training LSTM + 10K Monte Carlo... auto-refreshing</span></div>
    </Card>
  );

  const mc = sim.monte_carlo || {};
  const rm = mc.risk_metrics || {};
  const fc = mc.fan_chart || [];
  const dc = mc.distribution_chart || [];
  const ts = mc.terminal_stats || {};

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="custom-simulation">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-cyan-400" />
          <p className="text-xs font-semibold text-[hsl(var(--foreground))]">Forward Simulation</p>
          <span className="text-[9px] bg-cyan-500/10 text-cyan-400 px-1.5 py-0.5 rounded font-mono">LSTM + MC</span>
        </div>
        <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${(rm.expected_return_pct || 0) > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
          E[R]: {(rm.expected_return_pct || 0) >= 0 ? '+' : ''}{rm.expected_return_pct}%
        </span>
      </div>
      {fc.length > 2 && (
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={fc} margin={{ top: 5, right: 5, bottom: 5, left: -5 }}>
            <defs><linearGradient id="cfanInner" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#06b6d4" stopOpacity={0.18} /><stop offset="100%" stopColor="#06b6d4" stopOpacity={0.05} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 14% 14%)" />
            <XAxis dataKey="week" tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `W${v}`} interval={Math.max(1, Math.floor(fc.length / 8))} />
            <YAxis tick={{ fontSize: 8, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${(v / 1e5).toFixed(1)}L`} />
            <Tooltip contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
              formatter={(val, name) => [`₹${(val / 1e5).toFixed(2)}L`, { p50: 'Median', mean: 'Mean', p25: '25th', p75: '75th' }[name] || name]} />
            <Area type="monotone" dataKey="p75" stroke="none" fill="url(#cfanInner)" />
            <Area type="monotone" dataKey="p25" stroke="none" fill="hsl(222 18% 8%)" />
            <Line type="monotone" dataKey="p50" stroke="#06b6d4" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="mean" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4 4" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
      {dc.length > 2 && (
        <div className="mt-3">
          <p className="text-[9px] text-[hsl(var(--muted-foreground))] mb-1 uppercase tracking-wider">Terminal Return Distribution</p>
          <ResponsiveContainer width="100%" height={70}>
            <BarChart data={dc} margin={{ top: 2, right: 5, bottom: 2, left: -15 }}>
              <XAxis dataKey="return_pct" tick={{ fontSize: 7, fill: 'hsl(215 16% 70%)' }} tickFormatter={v => `${v}%`} interval={Math.floor(dc.length / 5)} />
              <YAxis tick={false} width={10} />
              <ReferenceLine x={0} stroke="hsl(215 16% 50%)" strokeDasharray="2 2" />
              <Bar dataKey="frequency">{dc.map((e, i) => <Cell key={i} fill={e.return_pct >= 0 ? 'hsla(186,92%,42%,0.6)' : 'hsla(0,72%,52%,0.5)'} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mt-3">
        {[
          { l: 'VaR 95%', v: `${rm.var_95_pct}%`, c: 'text-red-400' },
          { l: 'CVaR 95%', v: `${rm.cvar_95_pct}%`, c: 'text-red-400' },
          { l: 'Max Exp DD', v: `-${rm.max_expected_drawdown_pct}%`, c: 'text-red-400' },
          { l: 'Median Ret', v: `${(rm.median_return_pct || 0) >= 0 ? '+' : ''}${rm.median_return_pct}%`, c: (rm.median_return_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400' },
          { l: 'P(Profit)', v: `${rm.probability_of_profit_pct}%`, c: rm.probability_of_profit_pct >= 60 ? 'text-emerald-400' : 'text-amber-400' },
          { l: 'Terminal', v: `₹${((ts.median_value || 0) / 1e5).toFixed(1)}L`, c: 'text-cyan-400' },
        ].map(m => (<div key={m.l}><p className="text-[9px] text-[hsl(var(--muted-foreground))]">{m.l}</p><p className={`text-sm font-mono font-bold ${m.c}`}>{m.v}</p></div>))}
      </div>
    </Card>
  );
}

export default function CustomPortfolioDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [rebalancing, setRebalancing] = useState(false);
  const [rebalanceStocks, setRebalanceStocks] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const load = useCallback(async () => {
    try {
      const [pRes, hRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/custom-portfolios/${id}`),
        fetch(`${BACKEND_URL}/api/custom-portfolios/${id}/history`),
      ]);
      const pData = await pRes.json();
      const hData = await hRes.json();
      if (pData.detail) { setError(pData.detail); } else { setPortfolio(pData); }
      setHistory(hData.history || []);
    } catch { setError('Failed to load portfolio'); }
    setLoading(false);
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false); };

  const startRebalance = () => {
    setRebalancing(true);
    setRebalanceStocks((portfolio?.holdings || []).map(h => ({
      symbol: h.symbol, name: h.name, sector: h.sector, weight: h.weight,
    })));
  };

  const cancelRebalance = () => { setRebalancing(false); setRebalanceStocks([]); setError(null); };

  const addStock = (stock) => {
    if (rebalanceStocks.length >= 10) return;
    setRebalanceStocks([...rebalanceStocks, { symbol: stock.symbol, name: stock.name, sector: stock.sector, weight: 10 }]);
  };

  const removeStock = (symbol) => setRebalanceStocks(rebalanceStocks.filter(s => s.symbol !== symbol));

  const updateWeight = (symbol, w) => setRebalanceStocks(rebalanceStocks.map(s => s.symbol === symbol ? { ...s, weight: Math.max(1, Math.min(50, w)) } : s));

  const saveRebalance = async () => {
    if (rebalanceStocks.length === 0) { setError('Add at least 1 stock'); return; }
    setSaving(true); setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/custom-portfolios/${id}/rebalance`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: rebalanceStocks }),
      });
      const d = await res.json();
      if (d.detail) { setError(d.detail); } else {
        setPortfolio(d); setRebalancing(false); setRebalanceStocks([]);
        await load();
      }
    } catch { setError('Rebalance failed'); }
    setSaving(false);
  };

  const handleDelete = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/custom-portfolios/${id}`, { method: 'DELETE' });
      navigate('/watchlist');
    } catch { setError('Delete failed'); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" /></div>;
  if (!portfolio) return <div className="p-6 text-center text-sm text-[hsl(var(--muted-foreground))]">{error || 'Portfolio not found'}</div>;

  const holdings = portfolio.holdings || [];
  const pnl = portfolio.total_pnl || 0;
  const pnlPct = portfolio.total_pnl_pct || 0;
  const invested = portfolio.total_invested || 0;
  const currentVal = portfolio.current_value || invested;
  const realizedPnl = portfolio.realized_pnl || 0;
  const unrealizedPnl = portfolio.unrealized_pnl != null
    ? portfolio.unrealized_pnl
    : holdings.reduce((sum, h) => sum + (h.pnl || 0), 0);
  const cashBalance = portfolio.cash_balance || 0;

  // Sector data for pie
  const sectors = {};
  holdings.forEach(h => {
    const s = h.sector || 'Other';
    const val = (h.value && h.value > 0) ? h.value :
                (h.entry_price && h.quantity) ? h.entry_price * h.quantity :
                (h.weight || 10);
    sectors[s] = (sectors[s] || 0) + val;
  });
  const sectorTotal = Object.values(sectors).reduce((a, b) => a + b, 0) || 1;
  const sectorData = Object.entries(sectors).map(([name, val]) => ({ name, value: val, pct: ((val / sectorTotal) * 100).toFixed(1) })).sort((a, b) => b.value - a.value);

  return (
    <div className="p-3 sm:p-6 max-w-5xl mx-auto space-y-4 sm:space-y-5" data-testid="custom-portfolio-detail">
      {/* Header */}
      <div>
        <button onClick={() => navigate('/watchlist')} className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] mb-3" data-testid="back-btn">
          <ArrowLeft className="w-3.5 h-3.5" /> All Portfolios
        </button>
        <div className="p-5 rounded-xl border border-[hsl(var(--primary))]/30 bg-gradient-to-br from-[hsl(var(--primary))]/10 to-transparent">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-display font-bold text-[hsl(var(--foreground))]">{portfolio.name}</h1>
                <span className="text-[9px] bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] px-1.5 py-0.5 rounded font-mono">Custom</span>
                {portfolio.rebalance_count > 0 && (
                  <span className="text-[9px] bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded font-mono">{portfolio.rebalance_count}x rebalanced</span>
                )}
              </div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{holdings.length} stocks | Capital: ₹50L</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-mono font-bold text-[hsl(var(--foreground))]">
                <IndianRupee className="w-4 h-4 inline" />{currentVal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
              <p className={`text-sm font-mono flex items-center justify-end gap-0.5 ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {pnl >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                {pnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                <span className="ml-1 text-xs">({pnl >= 0 ? '+' : ''}{pnl.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })})</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-3">
            <button onClick={handleRefresh} disabled={refreshing} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50">
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh Prices
            </button>
            {!rebalancing && (
              <button onClick={startRebalance} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25" data-testid="rebalance-btn">
                <ArrowRightLeft className="w-3.5 h-3.5" /> Rebalance
              </button>
            )}
            <button onClick={() => setDeleteConfirm(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20">
              <Trash2 className="w-3.5 h-3.5" /> Delete
            </button>
          </div>
        </div>
      </div>

      {deleteConfirm && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span className="text-xs text-red-400">Delete this portfolio permanently?</span>
          <button onClick={handleDelete} className="px-3 py-1 rounded text-xs bg-red-500 text-white hover:bg-red-600">Yes, Delete</button>
          <button onClick={() => setDeleteConfirm(false)} className="px-3 py-1 rounded text-xs bg-[hsl(var(--surface-3))]">Cancel</button>
        </div>
      )}

      {/* Rebalance Mode */}
      {rebalancing && (
        <Card className="bg-[hsl(var(--card))] border-amber-500/30 p-4 space-y-3" data-testid="rebalance-panel">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="w-4 h-4 text-amber-400" />
              <p className="text-sm font-semibold text-amber-400">Rebalance Mode</p>
            </div>
            <button onClick={cancelRebalance} className="text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]">Cancel</button>
          </div>
          {rebalanceStocks.length < 10 && (
            <StockSearch onAdd={addStock} addedSymbols={new Set(rebalanceStocks.map(s => s.symbol))} />
          )}
          {rebalanceStocks.map(s => (
            <div key={s.symbol} className="flex items-center justify-between py-2 border-b border-[hsl(var(--border))]/30">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-medium">{s.symbol.replace('.NS', '')}</span>
                <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{s.name?.slice(0, 20)}</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => updateWeight(s.symbol, s.weight - 1)} className="w-5 h-5 rounded bg-[hsl(var(--surface-3))] flex items-center justify-center"><Minus className="w-3 h-3" /></button>
                <span className="text-xs font-mono w-8 text-center">{s.weight}%</span>
                <button onClick={() => updateWeight(s.symbol, s.weight + 1)} className="w-5 h-5 rounded bg-[hsl(var(--surface-3))] flex items-center justify-center"><Plus className="w-3 h-3" /></button>
                <button onClick={() => removeStock(s.symbol)} className="text-red-400 ml-2"><X className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          ))}
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button onClick={saveRebalance} disabled={saving} className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-amber-500 text-black hover:bg-amber-400 disabled:opacity-50" data-testid="save-rebalance-btn">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            {saving ? 'Saving...' : 'Save Rebalance'}
          </button>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          { l: 'Invested', v: `₹${(invested / 1e5).toFixed(2)}L` },
          { l: 'Current Value', v: `₹${(currentVal / 1e5).toFixed(2)}L` },
          {
            l: 'Unrealized P&L',
            v: `${unrealizedPnl >= 0 ? '+' : ''}₹${(Math.abs(unrealizedPnl) / 1e3).toFixed(1)}K`,
            color: unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-red-400',
            testId: 'stat-unrealized-pnl',
          },
          {
            l: 'Realized P&L',
            v: `${realizedPnl >= 0 ? '+' : ''}₹${(Math.abs(realizedPnl) / 1e3).toFixed(1)}K`,
            color: realizedPnl >= 0 ? 'text-emerald-400' : 'text-red-400',
            testId: 'stat-realized-pnl',
          },
          {
            l: 'Cash Balance',
            v: `₹${(cashBalance / 1e3).toFixed(1)}K`,
            color: 'text-amber-400',
            testId: 'stat-cash-balance',
          },
          { l: 'Rebalances', v: portfolio.rebalance_count || 0 },
        ].map(s => (
          <Card key={s.l} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-3" data-testid={s.testId}>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{s.l}</p>
            <p className={`text-base font-mono font-bold ${s.color || 'text-[hsl(var(--foreground))]'}`}>{s.v}</p>
          </Card>
        ))}
      </div>

      {/* Holdings + Sector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] overflow-hidden" data-testid="holdings-table">
            <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[550px]">
              <thead>
                <tr className="text-[10px] text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
                  <th className="py-2 px-3 text-left">Stock</th>
                  <th className="py-2 px-3 text-left">Sector</th>
                  <th className="py-2 px-3 text-right">Entry</th>
                  <th className="py-2 px-3 text-right">Current</th>
                  <th className="py-2 px-3 text-right">P&L %</th>
                  <th className="py-2 px-3 text-right">Weight</th>
                  <th className="py-2 px-3 text-right">Value</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h, i) => (
                  <tr key={i} className="border-b border-[hsl(var(--border))]/30 hover:bg-[hsl(var(--surface-2))]">
                    <td className="py-2 px-3 font-mono font-medium">{(h.symbol || '').replace('.NS', '')}</td>
                    <td className="py-2 px-3"><span className="text-[10px] bg-[hsl(var(--surface-3))] px-1.5 py-0.5 rounded">{h.sector || 'N/A'}</span></td>
                    <td className="py-2 px-3 text-right font-mono">{h.entry_price?.toFixed(1)}</td>
                    <td className="py-2 px-3 text-right font-mono">{h.current_price?.toFixed(1)}</td>
                    <td className={`py-2 px-3 text-right font-mono font-bold ${(h.pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {(h.pnl_pct || 0) >= 0 ? '+' : ''}{(h.pnl_pct || 0).toFixed(2)}%
                    </td>
                    <td className="py-2 px-3 text-right font-mono">{h.weight?.toFixed(1)}%</td>
                    <td className="py-2 px-3 text-right font-mono">{((h.value || 0) / 1e5).toFixed(2)}L</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </Card>
        </div>
        {sectorData.length > 0 && (
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4">
            <p className="text-xs font-semibold text-[hsl(var(--foreground))] mb-3">Sector Allocation</p>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={sectorData} cx="50%" cy="50%" innerRadius={35} outerRadius={65} dataKey="value" stroke="none">
                  {sectorData.map((_, i) => <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: 'hsl(222 18% 8%)', border: '1px solid hsl(222 14% 18%)', borderRadius: '8px', fontSize: '10px' }}
                  formatter={(val) => [`₹${(val / 1e5).toFixed(1)}L`]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1 mt-2">
              {sectorData.map((s, i) => (
                <div key={s.name} className="flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                    <span className="text-[hsl(var(--foreground))]">{s.name}</span>
                  </div>
                  <span className="font-mono font-bold">{s.pct}%</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Backtest + Simulation */}
      <CustomBacktest portfolioId={id} />
      <CustomSimulation portfolioId={id} />

      {/* History */}
      {history.length > 0 && (
        <div data-testid="history-section">
          <button onClick={() => setHistoryOpen(!historyOpen)} className="flex items-center gap-2 mb-2">
            <History className="w-4 h-4 text-[hsl(var(--primary))]" />
            <p className="text-sm font-semibold text-[hsl(var(--foreground))]">Tracking History</p>
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">{history.length} events</span>
            {historyOpen ? <ChevronDown className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" /> : <ChevronRight className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />}
          </button>
          {historyOpen && (
            <div className="space-y-2">
              {history.map((h, i) => (
                <Card key={i} className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${h.action === 'CREATED' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'}`}>
                      {h.action}
                    </span>
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
                      {new Date(h.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {(h.changes || []).map((c, j) => (
                      <span key={j} className={`text-[9px] px-1.5 py-0.5 rounded ${c.type === 'ADD' ? 'bg-emerald-500/10 text-emerald-400' : c.type === 'REMOVE' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                        {c.type === 'ADD' ? '+' : c.type === 'REMOVE' ? '-' : '~'} {c.symbol?.replace('.NS', '')}
                        {c.type === 'WEIGHT_CHANGE' && ` (${c.old_weight}%→${c.new_weight}%)`}
                        {c.type === 'ADD' && c.weight && ` ${c.weight}%`}
                      </span>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import {
  ArrowLeft, RefreshCw, Loader2, IndianRupee, ArrowUpRight, ArrowDownRight,
  History, Trash2, ArrowRightLeft, Search, Plus, X, Minus, Save, AlertTriangle,
  ChevronDown, ChevronRight
} from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

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

  // Sector data for pie
  const sectors = {};
  holdings.forEach(h => { sectors[h.sector || 'Other'] = (sectors[h.sector || 'Other'] || 0) + (h.value || 0); });
  const sectorTotal = Object.values(sectors).reduce((a, b) => a + b, 0) || 1;
  const sectorData = Object.entries(sectors).map(([name, val]) => ({ name, value: val, pct: ((val / sectorTotal) * 100).toFixed(1) })).sort((a, b) => b.value - a.value);

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-5" data-testid="custom-portfolio-detail">
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { l: 'Invested', v: `₹${(invested / 1e5).toFixed(1)}L` },
          { l: 'Current Value', v: `₹${(currentVal / 1e5).toFixed(1)}L` },
          { l: 'Holdings', v: holdings.length },
          { l: 'Rebalances', v: portfolio.rebalance_count || 0 },
        ].map(s => (
          <Card key={s.l} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-3">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{s.l}</p>
            <p className="text-base font-mono font-bold text-[hsl(var(--foreground))]">{s.v}</p>
          </Card>
        ))}
      </div>

      {/* Holdings + Sector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] overflow-hidden" data-testid="holdings-table">
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

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Search, Plus, X, Minus, Loader2, ArrowLeft, Save, AlertTriangle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const MAX_STOCKS = 10;

function StockSearch({ onAdd, addedSymbols }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await fetch(`${BACKEND_URL}/api/symbols?q=${encodeURIComponent(query)}`);
        const d = await res.json();
        setResults((d.symbols || []).filter(s => !addedSymbols.has(s.symbol)).slice(0, 8));
      } catch { setResults([]); }
      setSearching(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [query, addedSymbols]);

  return (
    <div className="relative" data-testid="stock-search">
      <div className="flex items-center gap-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2">
        <Search className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search NSE stocks (e.g. TCS, RELIANCE, HDFC)..."
          className="flex-1 bg-transparent text-sm text-[hsl(var(--foreground))] outline-none placeholder:text-[hsl(var(--muted-foreground))]"
          data-testid="stock-search-input"
        />
        {searching && <Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--muted-foreground))]" />}
      </div>
      {results.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg shadow-xl max-h-60 overflow-y-auto">
          {results.map(s => (
            <button key={s.symbol} onClick={() => { onAdd(s); setQuery(''); setResults([]); }}
              className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-[hsl(var(--surface-2))] text-sm"
              data-testid={`search-result-${s.symbol}`}>
              <div>
                <span className="font-mono font-medium text-[hsl(var(--foreground))]">{s.symbol.replace('.NS', '')}</span>
                <span className="ml-2 text-xs text-[hsl(var(--muted-foreground))]">{s.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-[hsl(var(--surface-3))] px-1.5 py-0.5 rounded">{s.sector}</span>
                <Plus className="w-4 h-4 text-emerald-400" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CustomPortfolioCreate() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [stocks, setStocks] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const addedSymbols = new Set(stocks.map(s => s.symbol));
  const totalWeight = stocks.reduce((sum, s) => sum + s.weight, 0);

  const handleAdd = (stock) => {
    if (stocks.length >= MAX_STOCKS) return;
    const equalWeight = Math.floor(100 / (stocks.length + 1));
    const newStocks = stocks.map(s => ({ ...s, weight: equalWeight }));
    newStocks.push({ symbol: stock.symbol, name: stock.name, sector: stock.sector, weight: equalWeight });
    setStocks(newStocks);
  };

  const handleRemove = (symbol) => {
    const filtered = stocks.filter(s => s.symbol !== symbol);
    if (filtered.length > 0) {
      const eq = Math.floor(100 / filtered.length);
      const last = 100 - eq * (filtered.length - 1);
      setStocks(filtered.map((s, i) => ({ ...s, weight: i === filtered.length - 1 ? last : eq })));
    } else {
      setStocks([]);
    }
  };

  const handleWeightChange = (symbol, newWeight) => {
    setStocks(stocks.map(s => s.symbol === symbol ? { ...s, weight: Math.max(1, Math.min(50, newWeight)) } : s));
  };

  const autoBalance = () => {
    if (stocks.length === 0) return;
    const eq = Math.floor(100 / stocks.length);
    const last = 100 - eq * (stocks.length - 1);
    setStocks(stocks.map((s, i) => ({ ...s, weight: i === stocks.length - 1 ? last : eq })));
  };

  const handleSave = async () => {
    if (!name.trim()) { setError('Give your portfolio a name'); return; }
    if (stocks.length === 0) { setError('Add at least 1 stock'); return; }
    setError(null);
    setSaving(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/custom-portfolios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          symbols: stocks.map(s => ({ symbol: s.symbol, name: s.name, weight: s.weight })),
          capital: 5000000,
        }),
      });
      const d = await res.json();
      if (d.detail) { setError(d.detail); setSaving(false); return; }
      if (d.id) {
        navigate(`/portfolio/custom/${d.id}`);
      }
    } catch (e) {
      setError('Failed to create portfolio');
    }
    setSaving(false);
  };

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto space-y-5" data-testid="create-portfolio-page">
      <button onClick={() => navigate('/watchlist')} className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]" data-testid="back-btn">
        <ArrowLeft className="w-3.5 h-3.5" /> All Portfolios
      </button>

      <div>
        <h1 className="text-xl font-display font-bold text-[hsl(var(--foreground))]">Make Your Own Portfolio</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Select up to 10 NSE stocks, set weights, and track performance with ₹50L notional capital.</p>
      </div>

      {/* Name */}
      <div>
        <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Portfolio Name</label>
        <input type="text" value={name} onChange={e => setName(e.target.value)} maxLength={40}
          placeholder="e.g. My Growth Picks, Dividend Kings..."
          className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2.5 text-sm text-[hsl(var(--foreground))] outline-none focus:border-[hsl(var(--primary))]"
          data-testid="portfolio-name-input" />
      </div>

      {/* Search */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs text-[hsl(var(--muted-foreground))]">Add Stocks ({stocks.length}/{MAX_STOCKS})</label>
          {stocks.length > 1 && (
            <button onClick={autoBalance} className="text-[10px] text-[hsl(var(--primary))] hover:underline" data-testid="auto-balance-btn">
              Auto-balance weights
            </button>
          )}
        </div>
        {stocks.length < MAX_STOCKS && <StockSearch onAdd={handleAdd} addedSymbols={addedSymbols} />}
      </div>

      {/* Selected Stocks */}
      {stocks.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] overflow-hidden" data-testid="selected-stocks">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
                <th className="py-2 px-3 text-left">Stock</th>
                <th className="py-2 px-3 text-left">Sector</th>
                <th className="py-2 px-3 text-center">Weight %</th>
                <th className="py-2 px-3 text-center">Allocation</th>
                <th className="py-2 px-3 text-center w-10"></th>
              </tr>
            </thead>
            <tbody>
              {stocks.map(s => (
                <tr key={s.symbol} className="border-b border-[hsl(var(--border))]/30" data-testid={`stock-row-${s.symbol}`}>
                  <td className="py-2.5 px-3">
                    <span className="font-mono font-medium text-[hsl(var(--foreground))]">{s.symbol.replace('.NS', '')}</span>
                    <span className="ml-1.5 text-[hsl(var(--muted-foreground))]">{s.name?.slice(0, 25)}</span>
                  </td>
                  <td className="py-2.5 px-3"><span className="text-[10px] bg-[hsl(var(--surface-3))] px-1.5 py-0.5 rounded">{s.sector}</span></td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center justify-center gap-1">
                      <button onClick={() => handleWeightChange(s.symbol, s.weight - 1)} className="w-5 h-5 rounded bg-[hsl(var(--surface-3))] flex items-center justify-center hover:bg-[hsl(var(--surface-2))]">
                        <Minus className="w-3 h-3" />
                      </button>
                      <input type="number" value={s.weight} onChange={e => handleWeightChange(s.symbol, parseInt(e.target.value) || 1)}
                        className="w-12 text-center bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded px-1 py-0.5 text-xs font-mono"
                        data-testid={`weight-input-${s.symbol}`} />
                      <button onClick={() => handleWeightChange(s.symbol, s.weight + 1)} className="w-5 h-5 rounded bg-[hsl(var(--surface-3))] flex items-center justify-center hover:bg-[hsl(var(--surface-2))]">
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono text-[hsl(var(--muted-foreground))]">
                    ₹{((5000000 * s.weight / Math.max(totalWeight, 1)) / 1e5).toFixed(1)}L
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <button onClick={() => handleRemove(s.symbol)} className="text-red-400 hover:text-red-300" data-testid={`remove-${s.symbol}`}>
                      <X className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between px-3 py-2 bg-[hsl(var(--surface-2))] border-t border-[hsl(var(--border))]">
            <span className="text-xs text-[hsl(var(--muted-foreground))]">{stocks.length} stocks</span>
            <span className={`text-xs font-mono font-bold ${totalWeight === 100 ? 'text-emerald-400' : 'text-amber-400'}`}>
              Total: {totalWeight}% {totalWeight !== 100 && '(will normalize)'}
            </span>
          </div>
        </Card>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {/* Save */}
      <div className="flex items-center gap-3 pt-2">
        <button onClick={handleSave} disabled={saving || stocks.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
          data-testid="save-portfolio-btn">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Creating...' : 'Create Portfolio'}
        </button>
        <button onClick={() => navigate('/watchlist')} className="px-4 py-2.5 rounded-lg text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]">
          Cancel
        </button>
      </div>

      {/* Playbook */}
      <Card className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] p-4 mt-4">
        <p className="text-xs font-semibold text-[hsl(var(--foreground))] mb-2">Portfolio Construction Playbook</p>
        <div className="space-y-1.5 text-[11px] text-[hsl(var(--muted-foreground))] leading-relaxed">
          <p>1. <strong>Diversify across sectors</strong> — Don't put more than 30% in any single sector. Spread risk.</p>
          <p>2. <strong>Size by conviction</strong> — Higher weight = higher conviction. But cap individual stocks at 20%.</p>
          <p>3. <strong>Mix time horizons</strong> — Blend long-term compounders with momentum plays.</p>
          <p>4. <strong>Mind liquidity</strong> — Stick to stocks with daily volume &gt; ₹5 Cr. You need to be able to exit.</p>
          <p>5. <strong>Set a stop-loss mentally</strong> — Before buying, decide at what loss % you'll exit. 8-10% is professional.</p>
          <p>6. <strong>Rebalance quarterly</strong> — Don't set and forget. Review every 3 months, trim winners, cut losers.</p>
          <p>7. <strong>Track against Nifty 50</strong> — If you can't beat the index, buy the index.</p>
        </div>
      </Card>
    </div>
  );
}

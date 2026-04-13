import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, TrendingUp, TrendingDown, RefreshCw, Edit3, X, Search, Briefcase, IndianRupee, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function AddStockModal({ open, onClose, stocks, onAdd }) {
  const [search, setSearch] = useState('');
  const [symbol, setSymbol] = useState('');
  const [scripCode, setScripCode] = useState('');
  const [name, setName] = useState('');
  const [entryPrice, setEntryPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [notes, setNotes] = useState('');

  const filteredStocks = stocks.filter(s =>
    !search || s.symbol?.toLowerCase().includes(search.toLowerCase()) ||
    s.name?.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 50);

  const selectStock = (s) => {
    setSymbol(s.symbol);
    setScripCode(s.scrip_code);
    setName(s.name);
    setSearch('');
  };

  const handleSubmit = () => {
    if (!symbol) return;
    onAdd({
      symbol, scrip_code: scripCode, name,
      entry_price: parseFloat(entryPrice) || 0,
      quantity: parseInt(quantity) || 0,
      notes,
    });
    setSymbol(''); setScripCode(''); setName('');
    setEntryPrice(''); setQuantity(''); setNotes('');
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="add-stock-modal-overlay" onClick={onClose}>
      <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-2xl w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()} data-testid="add-stock-modal">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[hsl(var(--border))]">
          <h3 className="text-base font-semibold text-[hsl(var(--foreground))]">Add to Watchlist</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-[hsl(var(--surface-3))]" data-testid="close-add-modal">
            <X className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          {!symbol ? (
            <div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <input type="text" placeholder="Search stock..." value={search} onChange={e => setSearch(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
                  data-testid="search-stock-add" autoFocus />
              </div>
              {search && (
                <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
                  {filteredStocks.map(s => (
                    <button key={s.scrip_code || s.symbol} onClick={() => selectStock(s)}
                      className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-[hsl(var(--surface-3))] text-left">
                      <span className="font-mono text-[hsl(var(--primary))]">{s.symbol}</span>
                      <span className="text-xs text-[hsl(var(--muted-foreground))] ml-2 truncate">{s.name?.slice(0, 25)}</span>
                    </button>
                  ))}
                  {filteredStocks.length === 0 && (
                    <p className="px-3 py-4 text-sm text-[hsl(var(--muted-foreground))] text-center">No stocks found</p>
                  )}
                </div>
              )}
              <div className="mt-3 text-center">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Or enter manually:</p>
                <input type="text" placeholder="Symbol (e.g. RELIANCE)" value={symbol}
                  onChange={e => setSymbol(e.target.value.toUpperCase())}
                  className="mt-2 w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))] text-center"
                  data-testid="manual-symbol-input" />
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20">
                <span className="font-mono font-bold text-[hsl(var(--primary))]">{symbol}</span>
                {name && <span className="text-xs text-[hsl(var(--muted-foreground))]">{name}</span>}
                <button onClick={() => { setSymbol(''); setName(''); setScripCode(''); }} className="ml-auto">
                  <X className="w-3 h-3 text-[hsl(var(--muted-foreground))]" />
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Entry Price</label>
                  <input type="number" placeholder="0.00" value={entryPrice} onChange={e => setEntryPrice(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
                    data-testid="entry-price-input" />
                </div>
                <div>
                  <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Quantity</label>
                  <input type="number" placeholder="0" value={quantity} onChange={e => setQuantity(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
                    data-testid="quantity-input" />
                </div>
              </div>
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Notes (optional)</label>
                <input type="text" placeholder="e.g. Long-term hold" value={notes} onChange={e => setNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
                  data-testid="notes-input" />
              </div>
              <button onClick={handleSubmit}
                className="w-full py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90"
                data-testid="confirm-add-btn">
                Add to Watchlist
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Watchlist() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stocks, setStocks] = useState([]);
  const [showAdd, setShowAdd] = useState(false);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/watchlist/summary`);
      const data = await res.json();
      setSummary(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  const fetchStocks = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/stocks`);
      const data = await res.json();
      setStocks(data.stocks || []);
    } catch (e) {}
  };

  useEffect(() => { fetchSummary(); fetchStocks(); }, [fetchSummary]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchSummary();
    setRefreshing(false);
  };

  const handleAdd = async (item) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/watchlist/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      const data = await res.json();
      toast.success(`${item.symbol} ${data.status === 'added' ? 'added to' : 'updated in'} watchlist`);
      fetchSummary();
    } catch (e) {
      toast.error('Failed to add stock');
    }
  };

  const handleRemove = async (symbol) => {
    try {
      await fetch(`${BACKEND_URL}/api/watchlist/${symbol}`, { method: 'DELETE' });
      toast.success(`${symbol} removed from watchlist`);
      fetchSummary();
    } catch (e) {
      toast.error('Failed to remove stock');
    }
  };

  const items = summary?.items || [];
  const hasPortfolio = items.some(i => i.entry_price > 0 && i.quantity > 0);

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-[1920px]" data-testid="watchlist-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-display font-bold text-[hsl(var(--foreground))]" data-testid="watchlist-title">
            Portfolio & Watchlist
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            Track your investments with live BSE prices
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90"
            data-testid="add-stock-btn">
            <Plus className="w-4 h-4" /> Add Stock
          </button>
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50"
            data-testid="refresh-prices-btn">
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Portfolio Summary */}
      {hasPortfolio && summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3" data-testid="portfolio-summary">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Invested</p>
              <p className="text-lg font-mono font-bold text-[hsl(var(--foreground))]">{summary.total_invested?.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Current Value</p>
              <p className="text-lg font-mono font-bold text-[hsl(var(--foreground))]">{summary.total_value?.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}</p>
            </CardContent>
          </Card>
          <Card className={`border ${summary.total_pnl >= 0 ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Total P&L</p>
              <p className={`text-lg font-mono font-bold ${summary.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {summary.total_pnl >= 0 ? '+' : ''}{summary.total_pnl?.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}
              </p>
            </CardContent>
          </Card>
          <Card className={`border ${summary.total_pnl_pct >= 0 ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Return %</p>
              <p className={`text-lg font-mono font-bold ${summary.total_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {summary.total_pnl_pct >= 0 ? '+' : ''}{summary.total_pnl_pct?.toFixed(2)}%
              </p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Winners</p>
              <p className="text-lg font-mono font-bold text-emerald-400">{summary.winners}</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Losers</p>
              <p className="text-lg font-mono font-bold text-red-400">{summary.losers}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Watchlist Items */}
      {loading ? (
        <div className="space-y-3" data-testid="watchlist-loading">
          {[...Array(4)].map((_, i) => <div key={i} className="h-20 rounded-lg bg-[hsl(var(--surface-2))] animate-pulse" />)}
        </div>
      ) : items.length === 0 ? (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-12 text-center">
            <Briefcase className="w-12 h-12 mx-auto mb-4 text-[hsl(var(--muted-foreground))]/40" />
            <h3 className="text-lg font-semibold text-[hsl(var(--foreground))] mb-2" data-testid="empty-watchlist-msg">No Stocks Yet</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">Start building your portfolio by adding stocks to your watchlist.</p>
            <button onClick={() => setShowAdd(true)}
              className="px-6 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
              data-testid="add-first-stock-btn">
              <Plus className="w-4 h-4 inline mr-2" /> Add First Stock
            </button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2" data-testid="watchlist-items">
          {items.map((item, idx) => (
            <div key={item.symbol}
              className="group flex items-center gap-4 p-4 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/30 transition-colors"
              data-testid={`watchlist-item-${idx}`}>

              {/* Symbol & Name */}
              <div className="min-w-0 flex-shrink-0 w-36">
                <span className="font-mono text-sm font-bold text-[hsl(var(--primary))]">{item.symbol}</span>
                {item.name && <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{item.name.slice(0, 25)}</p>}
              </div>

              {/* LTP & Change */}
              <div className="flex-shrink-0 w-28 text-right">
                {item.ltp ? (
                  <>
                    <p className="text-sm font-mono font-semibold text-[hsl(var(--foreground))]">
                      <IndianRupee className="w-3 h-3 inline" />{item.ltp?.toFixed(2)}
                    </p>
                    <p className={`text-xs font-mono flex items-center justify-end gap-0.5 ${item.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.change >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {item.change >= 0 ? '+' : ''}{item.change_pct?.toFixed(2)}%
                    </p>
                  </>
                ) : (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">No price</p>
                )}
              </div>

              {/* Entry Price */}
              <div className="hidden sm:block flex-shrink-0 w-24 text-right">
                {item.entry_price > 0 ? (
                  <>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Entry</p>
                    <p className="text-sm font-mono text-[hsl(var(--foreground))]">{item.entry_price?.toFixed(2)}</p>
                  </>
                ) : null}
              </div>

              {/* Qty */}
              <div className="hidden sm:block flex-shrink-0 w-16 text-right">
                {item.quantity > 0 && (
                  <>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Qty</p>
                    <p className="text-sm font-mono text-[hsl(var(--foreground))]">{item.quantity}</p>
                  </>
                )}
              </div>

              {/* P&L */}
              <div className="flex-1 text-right">
                {item.total_pnl !== undefined ? (
                  <>
                    <p className={`text-sm font-mono font-semibold ${item.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.pnl >= 0 ? '+' : ''}{item.total_pnl?.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}
                    </p>
                    <p className={`text-xs font-mono ${item.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.pnl_pct >= 0 ? '+' : ''}{item.pnl_pct?.toFixed(2)}%
                    </p>
                  </>
                ) : item.ltp ? (
                  <div className="flex items-center justify-end gap-1">
                    {item.change_pct >= 0 ?
                      <TrendingUp className="w-4 h-4 text-emerald-400" /> :
                      <TrendingDown className="w-4 h-4 text-red-400" />
                    }
                  </div>
                ) : null}
              </div>

              {/* Notes */}
              {item.notes && (
                <div className="hidden lg:block flex-shrink-0 max-w-32">
                  <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{item.notes}</p>
                </div>
              )}

              {/* Delete */}
              <button onClick={() => handleRemove(item.symbol)}
                className="flex-shrink-0 p-2 rounded-lg text-[hsl(var(--muted-foreground))] hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-opacity"
                data-testid={`remove-${item.symbol}`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <AddStockModal open={showAdd} onClose={() => setShowAdd(false)} stocks={stocks} onAdd={handleAdd} />
    </div>
  );
}

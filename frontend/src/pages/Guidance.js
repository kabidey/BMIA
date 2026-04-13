import React, { useState, useEffect, useCallback } from 'react';
import { Search, FileText, Download, RefreshCw, Filter, ChevronLeft, ChevronRight, ExternalLink, AlertCircle, Database } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Guidance() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [filters, setFilters] = useState({ symbol: '', category: '', search: '' });
  const [activeFilter, setActiveFilter] = useState({ symbol: '', category: '', search: '' });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);
  const [selectedStock, setSelectedStock] = useState(null);
  const [showStockList, setShowStockList] = useState(false);
  const [stockSearch, setStockSearch] = useState('');

  const fetchItems = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeFilter.symbol) params.set('symbol', activeFilter.symbol);
      if (activeFilter.category) params.set('category', activeFilter.category);
      if (activeFilter.search) params.set('search', activeFilter.search);
      params.set('page', p);
      params.set('limit', 40);

      const res = await fetch(`${BACKEND_URL}/api/guidance?${params}`);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.pages || 0);
      setPage(p);
    } catch (e) {
      console.error('Guidance fetch error:', e);
    }
    setLoading(false);
  }, [activeFilter]);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error('Stats error:', e);
    }
  };

  const fetchStocks = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/stocks`);
      const data = await res.json();
      setStocks(data.stocks || []);
    } catch (e) {
      console.error('Stocks error:', e);
    }
  };

  useEffect(() => { fetchStats(); fetchStocks(); }, []);
  useEffect(() => { fetchItems(1); }, [fetchItems]);

  const applyFilters = () => {
    setActiveFilter({ ...filters });
  };

  const clearFilters = () => {
    setFilters({ symbol: '', category: '', search: '' });
    setActiveFilter({ symbol: '', category: '', search: '' });
    setSelectedStock(null);
  };

  const selectStock = (stock) => {
    setSelectedStock(stock);
    setFilters(f => ({ ...f, symbol: stock.symbol }));
    setActiveFilter(f => ({ ...f, symbol: stock.symbol }));
    setShowStockList(false);
  };

  const triggerScrape = async () => {
    setScraping(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/scrape?days_back=7`, { method: 'POST' });
      const data = await res.json();
      if (data.job_id) {
        // Poll for completion
        let attempts = 0;
        while (attempts < 300) {
          await new Promise(r => setTimeout(r, 3000));
          attempts++;
          const pollRes = await fetch(`${BACKEND_URL}/api/guidance/scrape/${data.job_id}`);
          const pollData = await pollRes.json();
          if (pollData.status === 'complete') {
            fetchStats();
            fetchStocks();
            fetchItems(1);
            break;
          }
          if (pollData.status === 'error') break;
        }
      }
    } catch (e) {
      console.error('Scrape error:', e);
    }
    setScraping(false);
  };

  const formatDate = (d) => {
    if (!d) return '';
    try {
      const dt = new Date(d);
      return dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return d; }
  };

  const categoryColors = {
    'Board Meeting': 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    'Result': 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    'AGM/EGM': 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    'Dividend': 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    'Insider Trading': 'bg-red-500/15 text-red-400 border-red-500/30',
    'Corporate Action': 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  };

  const getCategoryStyle = (cat) => {
    if (!cat) return 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]';
    for (const [key, val] of Object.entries(categoryColors)) {
      if (cat.toLowerCase().includes(key.toLowerCase())) return val;
    }
    return 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]';
  };

  const filteredStocks = stocks.filter(s =>
    !stockSearch || s.symbol?.toLowerCase().includes(stockSearch.toLowerCase()) ||
    s.name?.toLowerCase().includes(stockSearch.toLowerCase())
  );

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-[1920px]" data-testid="guidance-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-display font-bold text-[hsl(var(--foreground))]" data-testid="guidance-title">
            Guidance
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            BSE Corporate Announcements, Filings & Regulatory Updates
          </p>
        </div>
        <button
          onClick={triggerScrape}
          disabled={scraping}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
          data-testid="scrape-trigger-btn"
        >
          <RefreshCw className={`w-4 h-4 ${scraping ? 'animate-spin' : ''}`} />
          {scraping ? 'Scraping...' : 'Refresh Data'}
        </button>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="guidance-stats">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Total Filings</p>
              <p className="text-2xl font-mono font-bold text-[hsl(var(--foreground))]">{stats.total_announcements?.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Stocks Covered</p>
              <p className="text-2xl font-mono font-bold text-[hsl(var(--primary))]">{stats.total_stocks}</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Last 7 Days</p>
              <p className="text-2xl font-mono font-bold text-emerald-400">{stats.recent_7d?.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Categories</p>
              <p className="text-2xl font-mono font-bold text-amber-400">{stats.categories?.length || 0}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <button
            onClick={() => setShowStockList(!showStockList)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-left"
            data-testid="stock-filter-btn"
          >
            <Database className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
            <span className={selectedStock ? 'text-[hsl(var(--foreground))]' : 'text-[hsl(var(--muted-foreground))]'}>
              {selectedStock ? `${selectedStock.symbol} — ${selectedStock.name}` : 'Select Stock...'}
            </span>
          </button>
          {showStockList && (
            <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg shadow-xl max-h-72 overflow-hidden" data-testid="stock-dropdown">
              <div className="p-2 border-b border-[hsl(var(--border))]">
                <input
                  type="text"
                  placeholder="Search stocks..."
                  value={stockSearch}
                  onChange={e => setStockSearch(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
                  data-testid="stock-search-input"
                  autoFocus
                />
              </div>
              <div className="overflow-y-auto max-h-52">
                {filteredStocks.slice(0, 100).map(s => (
                  <button
                    key={s.scrip_code}
                    onClick={() => selectStock(s)}
                    className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-[hsl(var(--surface-2))] text-left"
                  >
                    <div>
                      <span className="font-mono text-[hsl(var(--primary))]">{s.symbol}</span>
                      <span className="ml-2 text-[hsl(var(--muted-foreground))]">{s.name?.slice(0, 30)}</span>
                    </div>
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">{s.announcements} items</span>
                  </button>
                ))}
                {filteredStocks.length === 0 && (
                  <p className="p-4 text-sm text-[hsl(var(--muted-foreground))] text-center">No stocks found</p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
          <input
            type="text"
            placeholder="Search headlines..."
            value={filters.search}
            onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && applyFilters()}
            className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]"
            data-testid="headline-search-input"
          />
        </div>

        <select
          value={filters.category}
          onChange={e => { setFilters(f => ({ ...f, category: e.target.value })); setActiveFilter(f => ({ ...f, category: e.target.value })); }}
          className="px-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
          data-testid="category-filter"
        >
          <option value="">All Categories</option>
          {(stats?.categories || []).map(c => (
            <option key={c.name} value={c.name}>{c.name} ({c.count})</option>
          ))}
        </select>

        <div className="flex gap-2">
          <button onClick={applyFilters} className="px-4 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" data-testid="apply-filter-btn">
            <Filter className="w-4 h-4" />
          </button>
          {(activeFilter.symbol || activeFilter.category || activeFilter.search) && (
            <button onClick={clearFilters} className="px-3 py-2.5 rounded-lg text-sm text-[hsl(var(--muted-foreground))] bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]" data-testid="clear-filter-btn">
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--muted-foreground))]" data-testid="results-count">
          {total.toLocaleString()} results {activeFilter.symbol && `for "${activeFilter.symbol}"`}
        </p>
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            <button onClick={() => fetchItems(page - 1)} disabled={page <= 1} className="p-1.5 rounded bg-[hsl(var(--surface-2))] disabled:opacity-30" data-testid="prev-page-btn">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-[hsl(var(--muted-foreground))]">Page {page} of {totalPages}</span>
            <button onClick={() => fetchItems(page + 1)} disabled={page >= totalPages} className="p-1.5 rounded bg-[hsl(var(--surface-2))] disabled:opacity-30" data-testid="next-page-btn">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Items List */}
      {loading ? (
        <div className="space-y-3" data-testid="guidance-loading">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-[hsl(var(--surface-2))] animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-12 text-center">
            <AlertCircle className="w-10 h-10 mx-auto mb-3 text-[hsl(var(--muted-foreground))]" />
            <h3 className="font-display text-lg font-semibold text-[hsl(var(--foreground))] mb-1" data-testid="no-results-title">
              {stats?.total_announcements === 0 ? 'No Data Yet' : 'No Matching Results'}
            </h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
              {stats?.total_announcements === 0
                ? 'Click "Refresh Data" to scrape the latest BSE announcements.'
                : 'Try adjusting your filters or search terms.'}
            </p>
            {stats?.total_announcements === 0 && (
              <button onClick={triggerScrape} disabled={scraping} className="px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" data-testid="empty-scrape-btn">
                {scraping ? 'Scraping...' : 'Start Scraping'}
              </button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2" data-testid="guidance-items-list">
          {items.map((item, idx) => (
            <div
              key={item.news_id || idx}
              className={`group flex items-start gap-4 p-4 rounded-lg border transition-colors
                ${item.critical
                  ? 'bg-red-500/5 border-red-500/20 hover:border-red-500/40'
                  : 'bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/30'
                }`}
              data-testid={`guidance-item-${idx}`}
            >
              <div className="flex-shrink-0 mt-0.5">
                <FileText className={`w-5 h-5 ${item.pdf_url ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`} />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2 flex-wrap mb-1">
                  <span className="font-mono text-xs font-semibold text-[hsl(var(--primary))]" data-testid={`item-symbol-${idx}`}>
                    {item.stock_symbol}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getCategoryStyle(item.category)}`}>
                    {item.category || 'General'}
                  </span>
                  {item.critical && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 font-semibold">
                      CRITICAL
                    </span>
                  )}
                </div>

                <p className="text-sm text-[hsl(var(--foreground))] leading-snug mb-1" data-testid={`item-headline-${idx}`}>
                  {item.headline}
                </p>

                {item.more_text && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed line-clamp-2">
                    {item.more_text}
                  </p>
                )}

                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {formatDate(item.news_date)}
                  </span>
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {item.stock_name?.slice(0, 35)}
                  </span>
                </div>
              </div>

              {item.pdf_url && (
                <a
                  href={item.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/20 border border-[hsl(var(--primary))]/20"
                  data-testid={`item-pdf-${idx}`}
                >
                  <Download className="w-3.5 h-3.5" />
                  PDF
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Bottom Pagination */}
      {totalPages > 1 && !loading && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button onClick={() => fetchItems(page - 1)} disabled={page <= 1} className="px-3 py-1.5 rounded text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] disabled:opacity-30" data-testid="bottom-prev-btn">
            Previous
          </button>
          <span className="text-sm text-[hsl(var(--muted-foreground))] px-3">
            Page {page} of {totalPages} ({total.toLocaleString()} total)
          </span>
          <button onClick={() => fetchItems(page + 1)} disabled={page >= totalPages} className="px-3 py-1.5 rounded text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] disabled:opacity-30" data-testid="bottom-next-btn">
            Next
          </button>
        </div>
      )}
    </div>
  );
}

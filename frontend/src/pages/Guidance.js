import React, { useState, useEffect, useCallback } from 'react';
import { Search, FileText, Download, RefreshCw, Filter, ChevronLeft, ChevronRight, AlertCircle, Database, MessageSquare, Send, X, Sparkles, BookOpen, ExternalLink, Loader2, ArrowLeft, AlertTriangle, Users, CalendarDays, BarChart3, Star, Clock, Briefcase } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// ── AI Chat Panel ──────────────────────────────────────────────────────────
function AIChatPanel({ onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/guidance/suggestions`)
      .then(r => r.json())
      .then(d => setSuggestions(d.suggestions || []))
      .catch(() => {});
  }, []);

  const askQuestion = async (q) => {
    const question = q || input.trim();
    if (!question || loading) return;

    const userMsg = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));
      const res = await fetch(`${BACKEND_URL}/api/guidance/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, conversation_history: history }),
      });
      const data = await res.json();

      const aiMsg = {
        role: 'assistant',
        content: data.answer || data.error || 'No response',
        sources: data.sources || [],
        filings_retrieved: data.filings_retrieved || 0,
        stocks_in_context: data.stocks_in_context || [],
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}`, sources: [] }]);
    }
    setLoading(false);
  };

  const formatAnswer = (text) => {
    if (!text) return null;
    // Convert markdown-like formatting
    return text.split('\n').map((line, i) => {
      if (line.startsWith('### ') || line.startsWith('## ')) {
        return <h3 key={i} className="text-sm font-bold text-[hsl(var(--primary))] mt-3 mb-1">{line.replace(/^#+\s/, '')}</h3>;
      }
      if (line.startsWith('**Key Takeaways') || line.startsWith('Key Takeaways')) {
        return <h3 key={i} className="text-sm font-bold text-emerald-400 mt-3 mb-1 border-t border-[hsl(var(--border))] pt-2">{line.replace(/\*\*/g, '')}</h3>;
      }
      if (line.startsWith('- ') || line.startsWith('• ')) {
        return <li key={i} className="text-sm text-[hsl(var(--foreground))] ml-4 mb-0.5 list-disc">{renderBold(line.slice(2))}</li>;
      }
      if (line.startsWith('**') && line.endsWith('**')) {
        return <p key={i} className="text-sm font-semibold text-[hsl(var(--foreground))] mt-2 mb-0.5">{line.replace(/\*\*/g, '')}</p>;
      }
      if (line.trim() === '') return <br key={i} />;
      return <p key={i} className="text-sm text-[hsl(var(--foreground))] leading-relaxed">{renderBold(line)}</p>;
    });
  };

  const renderBold = (text) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-semibold text-[hsl(var(--foreground))]">{part.slice(2, -2)}</strong>;
      }
      // Highlight filing references like [1], [SYMBOL | Date | Category]
      const refParts = part.split(/(\[\d+\]|\[[A-Z]+\s*\|[^\]]+\])/g);
      return refParts.map((rp, j) => {
        if (/^\[\d+\]$/.test(rp) || /^\[[A-Z]+\s*\|/.test(rp)) {
          return <span key={`${i}-${j}`} className="text-[hsl(var(--primary))] font-mono text-xs bg-[hsl(var(--primary))]/10 px-1 rounded">{rp}</span>;
        }
        return rp;
      });
    });
  };

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] border-l border-[hsl(var(--border))]" data-testid="ai-chat-panel">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[hsl(var(--primary))]/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-[hsl(var(--primary))]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">Guidance AI</h3>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">RAG-powered filing analysis</p>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 rounded hover:bg-[hsl(var(--surface-3))]" data-testid="close-chat-btn">
          <X className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="chat-messages">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Sparkles className="w-8 h-8 mx-auto mb-3 text-[hsl(var(--primary))]/50" />
            <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
              Ask any question about BSE corporate filings
            </p>
            {suggestions.length > 0 && (
              <div className="space-y-2" data-testid="suggested-questions">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => askQuestion(s)}
                    className="block w-full text-left px-3 py-2 rounded-lg text-xs text-[hsl(var(--foreground))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] transition-colors"
                    data-testid={`suggestion-${i}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`${msg.role === 'user' ? 'flex justify-end' : ''}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tr-sm bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" data-testid={`user-msg-${idx}`}>
                <p className="text-sm">{msg.content}</p>
              </div>
            ) : (
              <div className="space-y-2" data-testid={`ai-msg-${idx}`}>
                <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                  <div className="prose-sm">{formatAnswer(msg.content)}</div>
                </div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="px-3">
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] mb-1 font-semibold uppercase tracking-wider">
                      Sources ({msg.filings_retrieved} filings analyzed)
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.sources.slice(0, 8).map((src, si) => (
                        <div
                          key={si}
                          className={`group flex items-center gap-1 px-2 py-1 rounded text-[10px] border ${
                            src.critical
                              ? 'bg-red-500/10 border-red-500/30 text-red-400'
                              : 'bg-[hsl(var(--surface-3))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]'
                          }`}
                        >
                          <span className="font-mono font-bold text-[hsl(var(--primary))]">{src.symbol}</span>
                          <span className="opacity-60">|</span>
                          <span>{src.date}</span>
                          {src.pdf_url && (
                            <a href={src.pdf_url} target="_blank" rel="noopener noreferrer" className="ml-0.5 opacity-60 hover:opacity-100">
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          )}
                        </div>
                      ))}
                      {msg.sources.length > 8 && (
                        <span className="text-[10px] text-[hsl(var(--muted-foreground))] self-center">+{msg.sources.length - 8} more</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] w-fit" data-testid="ai-loading">
            <Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--primary))]" />
            <span className="text-sm text-[hsl(var(--muted-foreground))]">Analyzing filings...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Ask about BSE filings..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && askQuestion()}
            className="flex-1 px-4 py-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:border-[hsl(var(--primary))]"
            data-testid="ai-chat-input"
            disabled={loading}
          />
          <button
            onClick={() => askQuestion()}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] disabled:opacity-40 hover:opacity-90"
            data-testid="ai-send-btn"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}


// ── Document Item Row ──────────────────────────────────────────────────────
function DocItem({ item, compact = false }) {
  const formatDate = (d) => {
    if (!d) return '';
    try {
      const dt = new Date(d);
      const now = new Date();
      const diffMs = now - dt;
      const diffH = diffMs / (1000 * 60 * 60);
      if (diffH < 1) return `${Math.floor(diffMs / 60000)}m`;
      if (diffH < 24) return `${Math.floor(diffH)}h`;
      if (diffH < 48) return '1d';
      if (diffH < 168) return `${Math.floor(diffH / 24)}d`;
      return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: diffH > 8760 ? 'numeric' : undefined });
    } catch { return d; }
  };

  return (
    <a href={item.pdf_url || '#'} target={item.pdf_url ? '_blank' : undefined} rel="noopener noreferrer"
      className={`group flex items-start gap-3 px-3 py-2.5 rounded-lg border transition-colors hover:border-[hsl(var(--primary))]/30 ${
        item.critical ? 'bg-red-500/5 border-red-500/20' : 'bg-[hsl(var(--card))] border-[hsl(var(--border))]/50'
      }`}
      data-testid={`doc-item-${item.news_id}`}>
      <FileText className={`w-4 h-4 mt-0.5 flex-shrink-0 ${item.pdf_url ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`} />
      <div className="flex-1 min-w-0">
        <p className={`${compact ? 'text-xs' : 'text-sm'} text-[hsl(var(--foreground))] leading-snug`}>
          {item.headline}
        </p>
        {!compact && item.more_text && (
          <p className="text-[11px] text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">{item.more_text}</p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono whitespace-nowrap">
          {formatDate(item.news_date)}
        </span>
        {item.pdf_url && (
          <Download className="w-3.5 h-3.5 text-[hsl(var(--primary))] opacity-0 group-hover:opacity-100 transition-opacity" />
        )}
      </div>
    </a>
  );
}

// ── Stock Documents View (Screener.in Style) ───────────────────────────────
function StockDocuments({ symbol, stockName, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    setLoading(true);
    fetch(`${BACKEND_URL}/api/guidance/stock/${encodeURIComponent(symbol)}/documents`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  if (loading) {
    return (
      <div className="space-y-4 p-4">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))]"><ArrowLeft className="w-4 h-4" /></button>
          <div className="h-6 w-48 bg-[hsl(var(--surface-2))] animate-pulse rounded" />
        </div>
        {[...Array(6)].map((_, i) => <div key={i} className="h-16 bg-[hsl(var(--surface-2))] animate-pulse rounded-lg" />)}
      </div>
    );
  }

  if (!data || data.total === 0) {
    return (
      <div className="p-4 space-y-4">
        <button onClick={onBack} className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to all stocks
        </button>
        <div className="text-center py-12">
          <AlertCircle className="w-10 h-10 mx-auto mb-3 text-[hsl(var(--muted-foreground))]" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">No documents found for {symbol}</p>
        </div>
      </div>
    );
  }

  const allDocs = [
    ...(data.announcements || []),
    ...(data.board_meetings || []),
    ...(data.results || []),
    ...(data.insider_activity || []),
    ...(data.agm_egm || []),
    ...(data.corporate_actions || []),
    ...(data.annual_reports || []),
    ...(data.credit_ratings || []),
  ];
  const filtered = searchTerm
    ? allDocs.filter(d => (d.headline || '').toLowerCase().includes(searchTerm.toLowerCase()))
    : null;

  const sections = [
    { key: 'announcements', label: 'Announcements', icon: Clock, items: data.announcements, color: 'text-[hsl(var(--foreground))]' },
    { key: 'important', label: 'Important', icon: Star, items: data.important, color: 'text-amber-400' },
    { key: 'results', label: 'Results', icon: BarChart3, items: data.results, color: 'text-emerald-400' },
    { key: 'board_meetings', label: 'Board Meetings', icon: Briefcase, items: data.board_meetings, color: 'text-blue-400' },
    { key: 'insider_activity', label: 'Insider / SAST', icon: Users, items: data.insider_activity, color: 'text-red-400' },
    { key: 'agm_egm', label: 'AGM / EGM', icon: CalendarDays, items: data.agm_egm, color: 'text-purple-400' },
    { key: 'corporate_actions', label: 'Corp. Actions', icon: AlertTriangle, items: data.corporate_actions, color: 'text-cyan-400' },
    { key: 'credit_ratings', label: 'Credit Ratings', icon: Star, items: data.credit_ratings, color: 'text-amber-400' },
    { key: 'annual_reports', label: 'Annual Reports', icon: BookOpen, items: data.annual_reports, color: 'text-[hsl(var(--primary))]' },
  ];

  return (
    <div className="space-y-5" data-testid="stock-documents-view">
      {/* Header */}
      <div>
        <button onClick={onBack} className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] mb-3" data-testid="stock-docs-back">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to all stocks
        </button>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-display font-bold text-[hsl(var(--foreground))]" data-testid="stock-docs-title">
              {data.stock_name || symbol}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs font-mono">{symbol}</Badge>
              {data.scrip_code && <Badge variant="outline" className="text-[10px]">BSE: {data.scrip_code}</Badge>}
              <span className="text-xs text-[hsl(var(--muted-foreground))]">{data.total} documents (3-month window)</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {data.bse_link && (
              <a href={data.bse_link} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                data-testid="bse-link">
                <ExternalLink className="w-3 h-3" /> All on BSE
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
        <input type="text" placeholder="Search all documents..." value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
          data-testid="stock-docs-search" />
      </div>

      {/* Search results */}
      {filtered ? (
        <div className="space-y-2">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">{filtered.length} results for "{searchTerm}"</p>
          {filtered.slice(0, 30).map((item, i) => <DocItem key={item.news_id || i} item={item} />)}
          {filtered.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">No matching documents</p>}
        </div>
      ) : (
        /* Tabbed sections — Screener.in style */
        <Tabs defaultValue="announcements" className="w-full" data-testid="stock-docs-tabs">
          <TabsList className="w-full flex flex-wrap h-auto gap-1 bg-[hsl(var(--surface-2))] p-1 rounded-lg">
            {sections.filter(s => s.items?.length > 0).map(s => (
              <TabsTrigger key={s.key} value={s.key} className="flex items-center gap-1.5 text-xs px-3 py-1.5 data-[state=active]:bg-[hsl(var(--card))] data-[state=active]:shadow-sm rounded-md"
                data-testid={`tab-${s.key}`}>
                <s.icon className={`w-3 h-3 ${s.color}`} />
                {s.label}
                <span className="text-[10px] opacity-60 font-mono">{s.items.length}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {sections.filter(s => s.items?.length > 0).map(s => (
            <TabsContent key={s.key} value={s.key} className="mt-3" data-testid={`panel-${s.key}`}>
              <ScrollArea className="max-h-[600px]">
                <div className="space-y-1.5">
                  {s.items.map((item, i) => <DocItem key={item.news_id || i} item={item} compact={s.key === 'annual_reports'} />)}
                </div>
              </ScrollArea>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}



// ── Main Guidance Page ─────────────────────────────────────────────────────
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
  const [chatOpen, setChatOpen] = useState(false);

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
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [activeFilter]);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/stats`);
      setStats(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchStocks = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/stocks`);
      const data = await res.json();
      setStocks(data.stocks || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchStats(); fetchStocks(); }, []);
  useEffect(() => { fetchItems(1); }, [fetchItems]);

  const applyFilters = () => setActiveFilter({ ...filters });
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
        let attempts = 0;
        while (attempts < 300) {
          await new Promise(r => setTimeout(r, 3000));
          attempts++;
          const pollRes = await fetch(`${BACKEND_URL}/api/guidance/scrape/${data.job_id}`);
          const pollData = await pollRes.json();
          if (pollData.status === 'complete' || pollData.status === 'error') {
            fetchStats(); fetchStocks(); fetchItems(1);
            break;
          }
        }
      }
    } catch (e) { console.error(e); }
    setScraping(false);
  };

  const formatDate = (d) => {
    if (!d) return '';
    try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return d; }
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
    <div className="flex h-[calc(100vh-56px)]" data-testid="guidance-page">
      {/* Main Content */}
      <div className={`flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 max-w-[1920px] ${chatOpen ? 'hidden lg:block' : ''}`}>
        {/* Show Stock Documents view when a stock is selected */}
        {selectedStock ? (
          <StockDocuments
            symbol={selectedStock.symbol}
            stockName={selectedStock.name}
            onBack={() => { setSelectedStock(null); clearFilters(); }}
          />
        ) : (
        <>
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-display font-bold text-[hsl(var(--foreground))]" data-testid="guidance-title">
              Guidance
            </h1>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
              BSE Corporate Announcements, Filings & AI Analysis
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setChatOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-[hsl(var(--primary))] to-purple-500 text-white hover:opacity-90 shadow-lg shadow-[hsl(var(--primary))]/20"
              data-testid="open-ai-chat-btn"
            >
              <Sparkles className="w-4 h-4" />
              Ask AI
            </button>
            <button
              onClick={triggerScrape}
              disabled={scraping}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50"
              data-testid="scrape-trigger-btn"
            >
              <RefreshCw className={`w-4 h-4 ${scraping ? 'animate-spin' : ''}`} />
              {scraping ? 'Scraping...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="guidance-stats">
            {[
              { label: 'Total Filings', value: stats.total_announcements?.toLocaleString(), color: 'text-[hsl(var(--foreground))]' },
              { label: 'Stocks Covered', value: stats.total_stocks, color: 'text-[hsl(var(--primary))]' },
              { label: 'Last 7 Days', value: stats.recent_7d?.toLocaleString(), color: 'text-emerald-400' },
              { label: 'Categories', value: stats.categories?.length || 0, color: 'text-amber-400' },
            ].map((s, i) => (
              <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{s.label}</p>
                  <p className={`text-2xl font-mono font-bold ${s.color}`}>{s.value}</p>
                </CardContent>
              </Card>
            ))}
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
                  <input type="text" placeholder="Search stocks..." value={stockSearch} onChange={e => setStockSearch(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
                    data-testid="stock-search-input" autoFocus />
                </div>
                <div className="overflow-y-auto max-h-52">
                  {filteredStocks.slice(0, 100).map(s => (
                    <button key={s.scrip_code} onClick={() => selectStock(s)}
                      className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-[hsl(var(--surface-2))] text-left">
                      <div>
                        <span className="font-mono text-[hsl(var(--primary))]">{s.symbol}</span>
                        <span className="ml-2 text-[hsl(var(--muted-foreground))]">{s.name?.slice(0, 30)}</span>
                      </div>
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">{s.announcements}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
            <input type="text" placeholder="Search headlines..." value={filters.search}
              onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
              onKeyDown={e => e.key === 'Enter' && applyFilters()}
              className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
              data-testid="headline-search-input" />
          </div>
          <select value={filters.category}
            onChange={e => { setFilters(f => ({ ...f, category: e.target.value })); setActiveFilter(f => ({ ...f, category: e.target.value })); }}
            className="px-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-sm text-[hsl(var(--foreground))]"
            data-testid="category-filter">
            <option value="">All Categories</option>
            {(stats?.categories || []).map(c => <option key={c.name} value={c.name}>{c.name} ({c.count})</option>)}
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

        {/* Count + Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-[hsl(var(--muted-foreground))]" data-testid="results-count">
            {total.toLocaleString()} results {activeFilter.symbol && `for "${activeFilter.symbol}"`}
          </p>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button onClick={() => fetchItems(page - 1)} disabled={page <= 1} className="p-1.5 rounded bg-[hsl(var(--surface-2))] disabled:opacity-30" data-testid="prev-page-btn"><ChevronLeft className="w-4 h-4" /></button>
              <span className="text-sm text-[hsl(var(--muted-foreground))]">Page {page}/{totalPages}</span>
              <button onClick={() => fetchItems(page + 1)} disabled={page >= totalPages} className="p-1.5 rounded bg-[hsl(var(--surface-2))] disabled:opacity-30" data-testid="next-page-btn"><ChevronRight className="w-4 h-4" /></button>
            </div>
          )}
        </div>

        {/* Items */}
        {loading ? (
          <div className="space-y-3" data-testid="guidance-loading">
            {[...Array(8)].map((_, i) => <div key={i} className="h-20 rounded-lg bg-[hsl(var(--surface-2))] animate-pulse" />)}
          </div>
        ) : items.length === 0 ? (
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-12 text-center">
              <AlertCircle className="w-10 h-10 mx-auto mb-3 text-[hsl(var(--muted-foreground))]" />
              <h3 className="font-display text-lg font-semibold text-[hsl(var(--foreground))] mb-1" data-testid="no-results-title">
                {stats?.total_announcements === 0 ? 'No Data Yet' : 'No Matching Results'}
              </h3>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
                {stats?.total_announcements === 0 ? 'Click "Refresh" to scrape the latest BSE announcements.' : 'Try adjusting your filters.'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2" data-testid="guidance-items-list">
            {items.map((item, idx) => (
              <div key={item.news_id || idx}
                className={`group flex items-start gap-4 p-4 rounded-lg border transition-colors ${
                  item.critical ? 'bg-red-500/5 border-red-500/20 hover:border-red-500/40' : 'bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/30'
                }`} data-testid={`guidance-item-${idx}`}>
                <FileText className={`w-5 h-5 flex-shrink-0 mt-0.5 ${item.pdf_url ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-2 flex-wrap mb-1">
                    <span className="font-mono text-xs font-semibold text-[hsl(var(--primary))]">{item.stock_symbol}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getCategoryStyle(item.category)}`}>{item.category || 'General'}</span>
                    {item.critical && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 font-semibold">CRITICAL</span>}
                  </div>
                  <p className="text-sm text-[hsl(var(--foreground))] leading-snug mb-1">{item.headline}</p>
                  {item.more_text && <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed line-clamp-2">{item.more_text}</p>}
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">{formatDate(item.news_date)}</span>
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">{item.stock_name?.slice(0, 35)}</span>
                  </div>
                </div>
                {item.pdf_url && (
                  <a href={item.pdf_url} target="_blank" rel="noopener noreferrer"
                    className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/20 border border-[hsl(var(--primary))]/20"
                    data-testid={`item-pdf-${idx}`}>
                    <Download className="w-3.5 h-3.5" /> PDF
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Bottom Pagination */}
        {totalPages > 1 && !loading && (
          <div className="flex items-center justify-center gap-2 pt-2">
            <button onClick={() => fetchItems(page - 1)} disabled={page <= 1} className="px-3 py-1.5 rounded text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] disabled:opacity-30">Previous</button>
            <span className="text-sm text-[hsl(var(--muted-foreground))] px-3">Page {page}/{totalPages}</span>
            <button onClick={() => fetchItems(page + 1)} disabled={page >= totalPages} className="px-3 py-1.5 rounded text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] disabled:opacity-30">Next</button>
          </div>
        )}
        </>
        )}
      </div>

      {/* AI Chat Panel */}
      {chatOpen && (
        <div className="w-full lg:w-[440px] flex-shrink-0" data-testid="ai-chat-container">
          <AIChatPanel onClose={() => setChatOpen(false)} />
        </div>
      )}

      {/* Mobile AI FAB */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 lg:hidden w-14 h-14 rounded-full bg-gradient-to-r from-[hsl(var(--primary))] to-purple-500 text-white shadow-xl flex items-center justify-center z-50"
          data-testid="ai-fab-btn"
        >
          <MessageSquare className="w-6 h-6" />
        </button>
      )}
    </div>
  );
}

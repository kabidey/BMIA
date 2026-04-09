import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { Loader2, ArrowUpDown, Brain, Zap, TrendingUp, TrendingDown, Minus, AlertTriangle, Info } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const ACTION_STYLES = {
  BUY: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  SELL: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30' },
  HOLD: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' },
  AVOID: { bg: 'bg-gray-500/15', text: 'text-gray-400', border: 'border-gray-500/30' },
};

const CONVICTION_STYLES = {
  HIGH: 'text-emerald-400',
  MEDIUM: 'text-amber-400',
  LOW: 'text-gray-400',
};

export default function BatchScanner() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [sector, setSector] = useState('all');
  const [sectors, setSectors] = useState([]);
  const [sortField, setSortField] = useState('rank');
  const [sortDir, setSortDir] = useState('asc');
  const [aiPowered, setAiPowered] = useState(false);
  const [provider, setProvider] = useState('openai');
  const [scanMeta, setScanMeta] = useState(null);
  const { batchAIScan, batchAnalyze, fetchApi } = useApi();
  const navigate = useNavigate();

  useEffect(() => {
    fetchApi('/api/sectors').then(d => setSectors(d.sectors || [])).catch(() => {});
  }, []);

  const runAIScan = async () => {
    setLoading(true);
    setResults([]);
    setLoadingStep('Gathering market data for all symbols...');
    try {
      const sectorParam = sector === 'all' ? undefined : sector;
      setTimeout(() => setLoadingStep('Computing 25+ technical indicators per stock...'), 3000);
      setTimeout(() => setLoadingStep('Fetching 30+ fundamental metrics...'), 6000);
      setTimeout(() => setLoadingStep('AI Intelligence Engine analyzing and ranking...'), 9000);
      setTimeout(() => setLoadingStep('Generating conviction scores and rationale...'), 12000);

      const data = await batchAIScan(undefined, sectorParam, provider);
      setResults(data.results || []);
      setAiPowered(data.ai_powered !== false);
      setScanMeta({
        provider: data.provider,
        model: data.model,
        generated_at: data.generated_at,
        total: data.total,
      });
    } catch (e) {
      console.error(e);
      // Fallback to basic scan
      try {
        const sectorParam = sector === 'all' ? undefined : sector;
        const data = await batchAnalyze(undefined, sectorParam);
        setResults(data.results || []);
        setAiPowered(false);
      } catch (e2) {
        console.error(e2);
      }
    }
    setLoading(false);
    setLoadingStep('');
  };

  useEffect(() => { runAIScan(); }, []);

  const sorted = [...results].sort((a, b) => {
    const aVal = a[sortField] ?? 999;
    const bVal = b[sortField] ?? 999;
    if (typeof aVal === 'string') {
      return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
    }
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir(field === 'rank' ? 'asc' : 'desc');
    }
  };

  const SortHeader = ({ field, children, className = '' }) => (
    <th
      className={`py-3 px-2 font-medium cursor-pointer hover:text-[hsl(var(--foreground))] ${className}`}
      style={{ transition: 'color 0.15s ease' }}
      onClick={() => toggleSort(field)}
    >
      <span className="flex items-center gap-1">
        {children}
        <ArrowUpDown className={`w-3 h-3 ${sortField === field ? 'text-[hsl(var(--primary))]' : ''}`} />
      </span>
    </th>
  );

  const getActionIcon = (action) => {
    switch (action) {
      case 'BUY': return <TrendingUp className="w-3.5 h-3.5" />;
      case 'SELL': return <TrendingDown className="w-3.5 h-3.5" />;
      case 'HOLD': return <Minus className="w-3.5 h-3.5" />;
      case 'AVOID': return <AlertTriangle className="w-3.5 h-3.5" />;
      default: return null;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px]" data-testid="batch-scanner-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary))]/20 flex items-center justify-center">
              <Brain className="w-6 h-6 text-[hsl(var(--primary))]" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold" data-testid="scanner-title">AI Batch Scanner</h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">AI-powered stock ranking with 25+ technical & 30+ fundamental parameters</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <Select value={sector} onValueChange={setSector}>
            <SelectTrigger className="w-40 bg-[hsl(var(--surface-2))]" data-testid="sector-filter">
              <SelectValue placeholder="All Sectors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sectors</SelectItem>
              {sectors.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <div className="flex gap-1">
            {['openai', 'claude', 'gemini'].map((p) => (
              <Button
                key={p}
                variant={provider === p ? 'default' : 'outline'}
                size="sm"
                onClick={() => setProvider(p)}
                className="text-xs capitalize"
                data-testid={`provider-${p}`}
              >
                {p}
              </Button>
            ))}
          </div>
          <Button onClick={runAIScan} disabled={loading} data-testid="scan-button">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Zap className="w-4 h-4 mr-2" />}
            {loading ? 'Scanning...' : 'AI Scan'}
          </Button>
        </div>
      </div>

      {/* AI Scan Meta */}
      {scanMeta && aiPowered && !loading && (
        <div className="flex items-center gap-4 text-xs text-[hsl(var(--muted-foreground))] bg-[hsl(var(--surface-2))] rounded-lg px-4 py-2 border border-[hsl(var(--primary))]/20">
          <Brain className="w-4 h-4 text-[hsl(var(--primary))]" />
          <span>AI-Powered Ranking</span>
          <span>Provider: <span className="text-[hsl(var(--foreground))] capitalize">{scanMeta.provider}</span></span>
          <span>Model: <span className="font-mono text-[hsl(var(--foreground))]">{scanMeta.model}</span></span>
          <span>Stocks: <span className="text-[hsl(var(--foreground))]">{scanMeta.total}</span></span>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-8">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="w-10 h-10 animate-spin text-[hsl(var(--primary))]" />
              <p className="text-sm font-medium text-[hsl(var(--primary))] animate-pulse">{loadingStep}</p>
              <div className="w-80 space-y-2">
                {['Gathering market data', 'Computing technical indicators', 'Fetching fundamentals', 'AI analyzing & ranking', 'Generating rationale'].map((step) => (
                  <div key={step} className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                    <div className={`w-2 h-2 rounded-full ${loadingStep.toLowerCase().includes(step.split(' ')[0].toLowerCase()) ? 'bg-[hsl(var(--primary))] animate-pulse' : 'bg-[hsl(var(--muted))]'}`} />
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Table */}
      {!loading && results.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="scanner-table">
                <thead>
                  <tr className="border-b border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] text-left">
                    <SortHeader field="rank">Rank</SortHeader>
                    <th className="py-3 px-2 font-medium">Symbol</th>
                    <th className="py-3 px-2 font-medium">Sector</th>
                    <SortHeader field="price">Price</SortHeader>
                    <SortHeader field="change_pct">Change %</SortHeader>
                    <SortHeader field="ai_score">AI Score</SortHeader>
                    <th className="py-3 px-2 font-medium">Action</th>
                    <th className="py-3 px-2 font-medium">Conviction</th>
                    <SortHeader field="rsi">RSI</SortHeader>
                    <th className="py-3 px-2 font-medium min-w-[280px]">AI Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((stock) => {
                    const actionStyle = ACTION_STYLES[stock.action] || ACTION_STYLES.HOLD;
                    return (
                      <tr
                        key={stock.symbol}
                        className="border-b border-[hsl(var(--border))]/50 hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                        style={{ transition: 'background-color 0.15s ease' }}
                        onClick={() => navigate(`/analyze/${encodeURIComponent(stock.symbol)}`)}
                        data-testid={`scanner-row-${stock.symbol}`}
                      >
                        <td className="py-3 px-2">
                          <span className="font-mono font-bold text-[hsl(var(--primary))] tabular-nums">
                            #{stock.rank || '-'}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <div>
                            <p className="font-mono font-medium tracking-wide">{stock.symbol.replace('.NS', '').replace('=F', '')}</p>
                            <p className="text-xs text-[hsl(var(--muted-foreground))]">{stock.name}</p>
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <Badge variant="secondary" className="text-xs">{stock.sector}</Badge>
                        </td>
                        <td className="py-3 px-2 font-mono tabular-nums text-right">
                          {stock.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                        </td>
                        <td className={`py-3 px-2 font-mono tabular-nums text-right ${(stock.change_pct || 0) >= 0 ? 'text-[hsl(var(--up))]' : 'text-[hsl(var(--down))]'}`}>
                          {(stock.change_pct || 0) >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2) || '0.00'}%
                        </td>
                        <td className="py-3 px-2 text-center">
                          {stock.ai_score != null ? (
                            <span className={`font-mono text-lg font-bold tabular-nums ${
                              stock.ai_score >= 70 ? 'text-[hsl(var(--up))]' :
                              stock.ai_score >= 40 ? 'text-amber-400' : 'text-[hsl(var(--down))]'
                            }`} data-testid="ai-score-value">
                              {stock.ai_score}
                            </span>
                          ) : (
                            <span className="text-[hsl(var(--muted-foreground))]">--</span>
                          )}
                        </td>
                        <td className="py-3 px-2">
                          <Badge className={`${actionStyle.bg} ${actionStyle.text} ${actionStyle.border} border text-xs gap-1`}>
                            {getActionIcon(stock.action)}
                            {stock.action || 'N/A'}
                          </Badge>
                        </td>
                        <td className="py-3 px-2">
                          <span className={`text-xs font-semibold ${CONVICTION_STYLES[stock.conviction] || 'text-gray-400'}`}>
                            {stock.conviction || 'N/A'}
                          </span>
                        </td>
                        <td className="py-3 px-2 font-mono tabular-nums text-right">{stock.rsi?.toFixed(1) || '--'}</td>
                        <td className="py-3 px-2">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <p className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2 max-w-[280px] cursor-help">
                                  {stock.rationale || 'No rationale available'}
                                </p>
                              </TooltipTrigger>
                              <TooltipContent side="left" className="max-w-sm">
                                <div className="space-y-1">
                                  <p className="text-xs">{stock.rationale}</p>
                                  {stock.key_strength && <p className="text-xs text-emerald-400">Strength: {stock.key_strength}</p>}
                                  {stock.key_risk && <p className="text-xs text-red-400">Risk: {stock.key_risk}</p>}
                                </div>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-12 text-center">
            <Brain className="w-16 h-16 text-[hsl(var(--muted-foreground))] mx-auto mb-4 opacity-20" />
            <h3 className="font-display text-xl font-semibold mb-2">No Results</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">Click AI Scan to analyze and rank stocks</p>
          </CardContent>
        </Card>
      )}

      {/* Disclaimer */}
      <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
        <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
          <strong>Disclaimer:</strong> AI-powered scan results are for educational purposes only. Rankings use AI analysis of 25+ technical indicators and 30+ fundamental metrics. Past performance does not guarantee future results. Always do your own research and consult a SEBI-registered advisor.
        </p>
      </div>
    </div>
  );
}

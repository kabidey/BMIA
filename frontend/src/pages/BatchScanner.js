import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Loader2, ArrowUpDown } from 'lucide-react';
import { useApi } from '../hooks/useApi';

export default function BatchScanner() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sector, setSector] = useState('all');
  const [sectors, setSectors] = useState([]);
  const [sortField, setSortField] = useState('alpha_score');
  const [sortDir, setSortDir] = useState('desc');
  const { batchAnalyze, fetchApi } = useApi();
  const navigate = useNavigate();

  useEffect(() => {
    fetchApi('/api/sectors').then(d => setSectors(d.sectors || [])).catch(() => {});
  }, []);

  const runScan = async () => {
    setLoading(true);
    try {
      const sectorParam = sector === 'all' ? undefined : sector;
      const data = await batchAnalyze(undefined, sectorParam);
      setResults(data.results || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { runScan(); }, []);

  const sorted = [...results].sort((a, b) => {
    const aVal = a[sortField] || 0;
    const bVal = b[sortField] || 0;
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const SortHeader = ({ field, children }) => (
    <th
      className="py-3 px-2 font-medium cursor-pointer hover:text-[hsl(var(--foreground))]"
      style={{ transition: 'color 0.15s ease' }}
      onClick={() => toggleSort(field)}
    >
      <span className="flex items-center gap-1">
        {children}
        <ArrowUpDown className={`w-3 h-3 ${sortField === field ? 'text-[hsl(var(--primary))]' : ''}`} />
      </span>
    </th>
  );

  return (
    <div className="p-6 space-y-6 max-w-[1600px]" data-testid="batch-scanner-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">Batch Scanner</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Scan Nifty 50 stocks with Alpha Score ranking</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={sector} onValueChange={setSector}>
            <SelectTrigger className="w-40 bg-[hsl(var(--surface-2))]" data-testid="sector-filter">
              <SelectValue placeholder="All Sectors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sectors</SelectItem>
              {sectors.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={runScan} disabled={loading} data-testid="scan-button">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            {loading ? 'Scanning...' : 'Run Scan'}
          </Button>
        </div>
      </div>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {Array(10).fill(0).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="scanner-table">
                <thead>
                  <tr className="border-b border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] text-left">
                    <th className="py-3 px-4 font-medium">#</th>
                    <th className="py-3 px-2 font-medium">Symbol</th>
                    <th className="py-3 px-2 font-medium">Sector</th>
                    <SortHeader field="price">Price</SortHeader>
                    <SortHeader field="change_pct">Change %</SortHeader>
                    <SortHeader field="rsi">RSI</SortHeader>
                    <SortHeader field="technical_score">Tech</SortHeader>
                    <SortHeader field="fundamental_score">Fund</SortHeader>
                    <SortHeader field="alpha_score">Alpha</SortHeader>
                    <th className="py-3 px-2 font-medium">Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((stock, i) => (
                    <tr
                      key={stock.symbol}
                      className="border-b border-[hsl(var(--border))]/50 hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                      style={{ transition: 'background-color 0.15s ease' }}
                      onClick={() => navigate(`/analyze/${encodeURIComponent(stock.symbol)}`)}
                      data-testid={`scanner-row-${stock.symbol}`}
                    >
                      <td className="py-3 px-4 text-[hsl(var(--muted-foreground))]">{i + 1}</td>
                      <td className="py-3 px-2">
                        <div>
                          <p className="font-mono font-medium">{stock.symbol.replace('.NS', '')}</p>
                          <p className="text-xs text-[hsl(var(--muted-foreground))]">{stock.name}</p>
                        </div>
                      </td>
                      <td className="py-3 px-2">
                        <Badge variant="secondary" className="text-xs">{stock.sector}</Badge>
                      </td>
                      <td className="py-3 px-2 font-mono tabular-nums text-right">
                        {stock.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </td>
                      <td className={`py-3 px-2 font-mono tabular-nums text-right ${stock.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct}%
                      </td>
                      <td className="py-3 px-2 font-mono tabular-nums text-right">{stock.rsi?.toFixed(1) || '--'}</td>
                      <td className="py-3 px-2 font-mono tabular-nums text-right">{stock.technical_score}</td>
                      <td className="py-3 px-2 font-mono tabular-nums text-right">{stock.fundamental_score}</td>
                      <td className="py-3 px-2 font-mono tabular-nums text-right font-bold text-[hsl(var(--primary))]" data-testid="alpha-score-value">
                        {stock.alpha_score}
                      </td>
                      <td className="py-3 px-2">
                        <Badge
                          style={{ backgroundColor: stock.recommendation_color, color: '#fff' }}
                          className="text-xs whitespace-nowrap"
                        >
                          {stock.recommendation}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
        <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
          <strong>Disclaimer:</strong> Batch scan results are for educational purposes only. Alpha scores combine technical (40%), fundamental (40%), and neutral sentiment (20%). Always do your own research and consult a SEBI-registered advisor.
        </p>
      </div>
    </div>
  );
}

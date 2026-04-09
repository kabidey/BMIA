import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import HeatmapGrid from '../components/charts/HeatmapGrid';

export default function MarketOverview() {
  const [overview, setOverview] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const { getOverview, getHeatmap } = useApi();
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [ov, hm] = await Promise.all([getOverview(), getHeatmap()]);
        setOverview(ov);
        setHeatmap(hm);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    }
    load();
  }, []);

  const formatPrice = (p) => {
    if (!p) return '--';
    return typeof p === 'number' ? p.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : p;
  };

  const formatVolume = (v) => {
    if (!v) return '--';
    if (v >= 10000000) return (v / 10000000).toFixed(2) + ' Cr';
    if (v >= 100000) return (v / 100000).toFixed(2) + ' L';
    if (v >= 1000) return (v / 1000).toFixed(1) + ' K';
    return v.toString();
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px]" data-testid="market-overview-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-[hsl(var(--foreground))]">Market Overview</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Real-time NSE/BSE market intelligence</p>
        </div>
        {overview && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
            Updated: {new Date(overview.timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* Top Gainers & Losers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gainers */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[hsl(var(--success))]" />
              Top Gainers
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)
            ) : (
              (overview?.gainers || []).map((stock) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] cursor-pointer card-hover"
                  style={{ transition: 'background-color 0.15s ease' }}
                  onClick={() => navigate(`/analyze/${encodeURIComponent(stock.symbol)}`)}
                  data-testid={`gainer-${stock.symbol}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-[hsl(var(--success))]/10 flex items-center justify-center">
                      <ArrowUpRight className="w-4 h-4 text-[hsl(var(--success))]" />
                    </div>
                    <div>
                      <p className="font-mono text-sm font-medium">{stock.symbol.replace('.NS', '')}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{stock.name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm tabular-nums">{formatPrice(stock.price)}</p>
                    <p className="text-xs font-mono tabular-nums text-up">+{stock.change_pct}%</p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Losers */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-[hsl(var(--danger))]" />
              Top Losers
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)
            ) : (
              (overview?.losers || []).map((stock) => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] cursor-pointer card-hover"
                  style={{ transition: 'background-color 0.15s ease' }}
                  onClick={() => navigate(`/analyze/${encodeURIComponent(stock.symbol)}`)}
                  data-testid={`loser-${stock.symbol}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-[hsl(var(--danger))]/10 flex items-center justify-center">
                      <ArrowDownRight className="w-4 h-4 text-[hsl(var(--danger))]" />
                    </div>
                    <div>
                      <p className="font-mono text-sm font-medium">{stock.symbol.replace('.NS', '')}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{stock.name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm tabular-nums">{formatPrice(stock.price)}</p>
                    <p className="text-xs font-mono tabular-nums text-down">{stock.change_pct}%</p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Heatmap */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-display">Sector Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="grid grid-cols-4 gap-2">
              {Array(16).fill(0).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
          ) : (
            <HeatmapGrid data={heatmap?.heatmap || {}} onSelect={(sym) => navigate(`/analyze/${encodeURIComponent(sym)}`)} />
          )}
        </CardContent>
      </Card>

      {/* All Stocks Table */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-display">All Tracked Stocks</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-10 w-full mb-2" />)
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="overview-table">
                <thead>
                  <tr className="border-b border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]">
                    <th className="text-left py-3 px-2 font-medium">Symbol</th>
                    <th className="text-left py-3 px-2 font-medium">Name</th>
                    <th className="text-left py-3 px-2 font-medium">Sector</th>
                    <th className="text-right py-3 px-2 font-medium">Price</th>
                    <th className="text-right py-3 px-2 font-medium">Change</th>
                    <th className="text-right py-3 px-2 font-medium">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {(overview?.all || []).map((stock) => (
                    <tr
                      key={stock.symbol}
                      className="border-b border-[hsl(var(--border))]/50 hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                      style={{ transition: 'background-color 0.15s ease' }}
                      onClick={() => navigate(`/analyze/${encodeURIComponent(stock.symbol)}`)}
                    >
                      <td className="py-3 px-2 font-mono font-medium">{stock.symbol.replace('.NS', '')}</td>
                      <td className="py-3 px-2 text-[hsl(var(--muted-foreground))]">{stock.name}</td>
                      <td className="py-3 px-2">
                        <Badge variant="secondary" className="text-xs">{stock.sector}</Badge>
                      </td>
                      <td className="py-3 px-2 text-right font-mono tabular-nums">{formatPrice(stock.price)}</td>
                      <td className={`py-3 px-2 text-right font-mono tabular-nums ${stock.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct}%
                      </td>
                      <td className="py-3 px-2 text-right font-mono tabular-nums text-[hsl(var(--muted-foreground))]">
                        {formatVolume(stock.volume)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SEBI Disclaimer */}
      <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
        <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
          <strong>Disclaimer:</strong> This tool is for educational and informational purposes only. It does not constitute investment advice, financial advice, or any recommendation to buy, sell, or hold securities. Past performance is not indicative of future results. Always consult a SEBI-registered investment advisor before making investment decisions. Invest at your own risk.
        </p>
      </div>
    </div>
  );
}

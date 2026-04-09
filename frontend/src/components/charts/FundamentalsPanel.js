import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';

export default function FundamentalsPanel({ data }) {
  if (!data) return null;

  const metrics = [
    { label: 'P/E Ratio', value: data.pe_ratio, suffix: 'x', info: 'Price to Earnings' },
    { label: 'Debt/Equity', value: data.debt_to_equity, suffix: '', info: 'Debt to Equity ratio' },
    { label: 'Revenue Growth', value: data.revenue_growth, suffix: '%', info: 'TTM Revenue Growth' },
    { label: 'EPS', value: data.eps, suffix: '', info: 'Earnings Per Share' },
    { label: 'Book Value', value: data.bvps, suffix: '', info: 'Book Value Per Share' },
    { label: 'ROE', value: data.roe, suffix: '%', info: 'Return on Equity' },
    { label: 'Profit Margin', value: data.profit_margin, suffix: '%', info: 'Net Profit Margin' },
    { label: 'Dividend Yield', value: data.dividend_yield, suffix: '%', info: 'Annual Dividend Yield' },
  ];

  const formatVal = (v, suffix) => {
    if (v === null || v === undefined) return 'N/A';
    return typeof v === 'number' ? v.toLocaleString('en-IN', { maximumFractionDigits: 2 }) + suffix : v;
  };

  const formatMarketCap = (mc) => {
    if (!mc) return 'N/A';
    if (mc >= 1e12) return (mc / 1e12).toFixed(2) + 'T';
    if (mc >= 1e9) return (mc / 1e9).toFixed(2) + 'B';
    if (mc >= 1e7) return (mc / 1e7).toFixed(2) + ' Cr';
    return mc.toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Score and Valuation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Fundamental Score</p>
            <p className="font-mono text-4xl font-bold tabular-nums text-[hsl(var(--primary))] mt-2">
              {data.fundamental_score}
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">out of 100</p>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Graham's Intrinsic Value</p>
            <p className="font-mono text-3xl font-bold tabular-nums mt-2">
              {data.graham_value ? `${data.graham_value.toLocaleString('en-IN')}` : 'N/A'}
            </p>
            {data.graham_value && data.current_price && (
              <Badge
                variant={data.valuation === 'Undervalued' ? 'default' : data.valuation === 'Overvalued' ? 'destructive' : 'secondary'}
                className="mt-2"
              >
                {data.valuation}
              </Badge>
            )}
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 font-mono">
              V = sqrt(22.5 x EPS x BVPS)
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Market Cap</p>
            <p className="font-mono text-3xl font-bold tabular-nums mt-2">{formatMarketCap(data.market_cap)}</p>
            <div className="flex justify-center gap-2 mt-2">
              <Badge variant="outline" className="text-xs">{data.sector || 'N/A'}</Badge>
              <Badge variant="outline" className="text-xs">{data.industry || 'N/A'}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metrics Grid */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-display">Key Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {metrics.map((m) => (
              <div key={m.label} className="bg-[hsl(var(--surface-2))] rounded-lg p-4">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{m.label}</p>
                <p className="font-mono text-xl font-bold tabular-nums mt-1">{formatVal(m.value, m.suffix)}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{m.info}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

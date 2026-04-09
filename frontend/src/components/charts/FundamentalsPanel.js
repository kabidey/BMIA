import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';

export default function FundamentalsPanel({ data }) {
  if (!data) return null;

  const formatVal = (v, suffix = '') => {
    if (v === null || v === undefined) return 'N/A';
    return typeof v === 'number' ? v.toLocaleString('en-IN', { maximumFractionDigits: 2 }) + suffix : String(v);
  };

  const formatLarge = (mc) => {
    if (!mc) return 'N/A';
    if (mc >= 1e12) return (mc / 1e12).toFixed(2) + 'T';
    if (mc >= 1e9) return (mc / 1e9).toFixed(2) + 'B';
    if (mc >= 1e7) return (mc / 1e7).toFixed(2) + ' Cr';
    return mc.toLocaleString();
  };

  const MetricCard = ({ label, value, suffix = '', info = '', highlight = false }) => (
    <div className={`bg-[hsl(var(--surface-2))] rounded-lg p-3 ${
      highlight ? 'border border-[hsl(var(--primary))]/20' : ''
    }`}>
      <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider">{label}</p>
      <p className={`font-mono text-base font-bold tabular-nums mt-0.5 ${
        highlight ? 'text-[hsl(var(--primary))]' : ''
      }`}>{formatVal(value, suffix)}</p>
      {info && <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{info}</p>}
    </div>
  );

  return (
    <div className="space-y-6" data-testid="fundamentals-panel">
      {/* Top KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Graham's Intrinsic Value</p>
            <p className="font-mono text-3xl font-bold tabular-nums mt-2">
              {data.graham_value ? `\u20B9${data.graham_value.toLocaleString('en-IN')}` : 'N/A'}
            </p>
            {data.graham_value && data.current_price && (
              <Badge
                variant={data.valuation?.includes('Under') ? 'default' : data.valuation?.includes('Over') ? 'destructive' : 'secondary'}
                className="mt-2"
                data-testid="valuation-badge"
              >
                {data.valuation}
              </Badge>
            )}
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 font-mono">V = sqrt(22.5 x EPS x BVPS)</p>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Market Cap</p>
            <p className="font-mono text-3xl font-bold tabular-nums mt-2" data-testid="market-cap">{formatLarge(data.market_cap)}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">EV: {formatLarge(data.enterprise_value)}</p>
            <div className="flex justify-center gap-2 mt-2">
              <Badge variant="outline" className="text-xs">{data.sector || 'N/A'}</Badge>
              <Badge variant="outline" className="text-xs">{data.industry || 'N/A'}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Free Cash Flow Yield</p>
            <p className={`font-mono text-3xl font-bold tabular-nums mt-2 ${
              (data.fcf_yield || 0) > 5 ? 'text-[hsl(var(--up))]' : (data.fcf_yield || 0) > 0 ? 'text-[hsl(var(--foreground))]' : 'text-[hsl(var(--down))]'
            }`} data-testid="fcf-yield">
              {data.fcf_yield != null ? `${data.fcf_yield}%` : 'N/A'}
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              FCF: {formatLarge(data.free_cashflow)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Valuation Ratios */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-display">Valuation Ratios</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            <MetricCard label="P/E (TTM)" value={data.pe_ratio} suffix="x" />
            <MetricCard label="P/E (Fwd)" value={data.forward_pe} suffix="x" />
            <MetricCard label="PEG Ratio" value={data.peg_ratio} suffix="x" highlight={data.peg_ratio && data.peg_ratio < 1} />
            <MetricCard label="Price/Sales" value={data.price_to_sales} suffix="x" />
            <MetricCard label="Price/Book" value={data.price_to_book} suffix="x" />
            <MetricCard label="EV/EBITDA" value={data.ev_to_ebitda} suffix="x" />
            <MetricCard label="EV/Revenue" value={data.ev_to_revenue} suffix="x" />
          </div>
        </CardContent>
      </Card>

      {/* Profitability & Growth */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display">Profitability</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <MetricCard label="Gross Margin" value={data.gross_margin} suffix="%" />
              <MetricCard label="Operating Margin" value={data.operating_margin} suffix="%" />
              <MetricCard label="Profit Margin" value={data.profit_margin} suffix="%" />
              <MetricCard label="ROE" value={data.roe} suffix="%" highlight={data.roe && data.roe > 15} />
              <MetricCard label="ROA" value={data.roa} suffix="%" />
              <MetricCard label="EPS (TTM)" value={data.eps} />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display">Growth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <MetricCard label="Revenue Growth" value={data.revenue_growth} suffix="%" highlight={data.revenue_growth && data.revenue_growth > 10} />
              <MetricCard label="Earnings Growth" value={data.earnings_growth} suffix="%" />
              <MetricCard label="Qtr Earnings Growth" value={data.earnings_quarterly_growth} suffix="%" />
              <MetricCard label="Forward EPS" value={data.forward_eps} />
              <MetricCard label="Revenue/Share" value={data.revenue_per_share} />
              <MetricCard label="Book Value/Share" value={data.bvps} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Balance Sheet & Cash Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display">Balance Sheet & Liquidity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <MetricCard label="Debt/Equity" value={data.debt_to_equity} highlight={data.debt_to_equity && data.debt_to_equity > 100} />
              <MetricCard label="Debt/EBITDA" value={data.debt_to_ebitda} suffix="x" />
              <MetricCard label="Current Ratio" value={data.current_ratio} suffix="x" />
              <MetricCard label="Quick Ratio" value={data.quick_ratio} suffix="x" />
              <MetricCard label="Total Debt" value={formatLarge(data.total_debt)} />
              <MetricCard label="Net Cash" value={formatLarge(data.net_cash)} highlight={data.net_cash && data.net_cash > 0} />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display">Cash Flow & Dividends</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <MetricCard label="Free Cash Flow" value={formatLarge(data.free_cashflow)} />
              <MetricCard label="Operating CF" value={formatLarge(data.operating_cashflow)} />
              <MetricCard label="FCF Yield" value={data.fcf_yield} suffix="%" />
              <MetricCard label="Dividend Yield" value={data.dividend_yield} suffix="%" />
              <MetricCard label="Dividend Rate" value={data.dividend_rate} />
              <MetricCard label="Payout Ratio" value={data.payout_ratio} suffix="%" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risk & Ownership */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-display">Risk & Ownership</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <MetricCard label="Beta" value={data.beta} highlight={data.beta && data.beta > 1.5} />
            <MetricCard label="Insider Holdings" value={data.held_pct_insiders} suffix="%" />
            <MetricCard label="Institutional" value={data.held_pct_institutions} suffix="%" />
            <MetricCard label="Short Ratio" value={data.short_ratio} />
            <MetricCard label="52W High" value={data.fifty_two_week_high} />
            <MetricCard label="52W Low" value={data.fifty_two_week_low} />
          </div>
        </CardContent>
      </Card>

      {/* Quarterly Financials */}
      {((data.quarterly_revenue && data.quarterly_revenue.length > 0) ||
        (data.quarterly_earnings && data.quarterly_earnings.length > 0)) && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-display">Quarterly Financials</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="quarterly-table">
                <thead>
                  <tr className="border-b border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] text-left">
                    <th className="py-2 px-3 font-medium">Quarter</th>
                    <th className="py-2 px-3 font-medium text-right">Revenue</th>
                    <th className="py-2 px-3 font-medium text-right">Net Income</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.quarterly_revenue || []).map((qr, i) => {
                    const qe = (data.quarterly_earnings || [])[i];
                    return (
                      <tr key={qr.quarter} className="border-b border-[hsl(var(--border))]/30">
                        <td className="py-2 px-3 font-mono text-xs">{qr.quarter}</td>
                        <td className="py-2 px-3 font-mono tabular-nums text-right">{formatLarge(qr.revenue)}</td>
                        <td className={`py-2 px-3 font-mono tabular-nums text-right ${
                          qe?.net_income && qe.net_income > 0 ? 'text-[hsl(var(--up))]' : qe?.net_income && qe.net_income < 0 ? 'text-[hsl(var(--down))]' : ''
                        }`}>{qe ? formatLarge(qe.net_income) : 'N/A'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

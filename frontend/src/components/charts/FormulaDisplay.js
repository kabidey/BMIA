import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

export default function FormulaDisplay({ alpha }) {
  const formulas = [
    {
      name: 'Alpha Score',
      latex: 'Alpha = 0.4 \\times Technical + 0.4 \\times Fundamental + 0.2 \\times Sentiment',
      explanation: 'Weighted combination of three analysis pillars to produce a final conviction score.',
      value: alpha?.alpha_score ? `${alpha.alpha_score}%` : null,
    },
    {
      name: "Graham's Intrinsic Value",
      latex: 'V = \\sqrt{22.5 \\times EPS \\times BVPS}',
      explanation: 'Benjamin Graham formula for estimating fair value using earnings and book value.',
      value: null,
    },
    {
      name: 'Momentum Score',
      latex: 'M = \\frac{Price_{now} - Price_{n}}{Price_{n} \\times Volume_{ratio}}',
      explanation: 'Measures price momentum adjusted for volume intensity over the lookback period.',
      value: alpha?.momentum ? alpha.momentum.toFixed(4) : null,
    },
    {
      name: 'Sharpe Ratio',
      latex: 'S_p = \\frac{R_p - R_f}{\\sigma_p}',
      explanation: 'Risk-adjusted return metric. Higher values indicate better risk-adjusted performance. Risk-free rate assumed at 6.5% (India 10Y yield).',
      value: alpha?.sharpe_ratio ? alpha.sharpe_ratio.toFixed(4) : null,
    },
    {
      name: 'RSI (Relative Strength Index)',
      latex: 'RSI = 100 - \\frac{100}{1 + \\frac{AvgGain_{14}}{AvgLoss_{14}}}',
      explanation: 'Measures overbought (>70) and oversold (<30) conditions over 14 periods.',
      value: null,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="mb-4">
        <h3 className="font-display text-lg font-semibold">Analytical Formulas</h3>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">Mathematical models powering the Alpha Score computation</p>
      </div>
      {formulas.map((f, i) => (
        <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-display font-semibold text-sm mb-2">{f.name}</h4>
                <div className="bg-[hsl(var(--surface-2))] rounded-lg p-4 mb-3 font-mono text-sm text-[hsl(var(--primary))] overflow-x-auto">
                  {f.latex}
                </div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">{f.explanation}</p>
              </div>
              {f.value && (
                <div className="ml-4 text-right">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Current</p>
                  <p className="font-mono text-lg font-bold tabular-nums text-[hsl(var(--primary))]">{f.value}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

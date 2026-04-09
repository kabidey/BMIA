import React from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

export default function HeatmapGrid({ data, onSelect }) {
  if (!data || Object.keys(data).length === 0) {
    return <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">No heatmap data available</p>;
  }

  const getColor = (changePct) => {
    if (changePct > 2) return 'bg-[hsl(142,70%,35%)]';
    if (changePct > 1) return 'bg-[hsl(142,70%,30%)]';
    if (changePct > 0) return 'bg-[hsl(142,50%,20%)]';
    if (changePct > -1) return 'bg-[hsl(0,50%,20%)]';
    if (changePct > -2) return 'bg-[hsl(0,70%,30%)]';
    return 'bg-[hsl(0,70%,35%)]';
  };

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {Object.entries(data).map(([sector, stocks]) => (
          <div key={sector}>
            <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-2 uppercase tracking-wide">{sector}</p>
            <div className="flex flex-wrap gap-2">
              {stocks.map((stock) => (
                <Tooltip key={stock.symbol}>
                  <TooltipTrigger asChild>
                    <button
                      className={`${getColor(stock.change_pct)} rounded-lg p-3 min-w-[100px] text-center cursor-pointer hover:opacity-80 border border-transparent hover:border-[hsl(var(--border))]`}
                      style={{ transition: 'opacity 0.15s ease, border-color 0.15s ease' }}
                      onClick={() => onSelect(stock.symbol)}
                      data-testid="heatmap-tile"
                    >
                      <p className="font-mono text-xs font-bold text-white">{stock.symbol.replace('.NS', '')}</p>
                      <p className={`font-mono text-sm font-bold tabular-nums ${stock.change_pct >= 0 ? 'text-green-100' : 'text-red-100'}`}>
                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct}%
                      </p>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <div className="text-sm">
                      <p className="font-semibold">{stock.name}</p>
                      <p className="font-mono">Price: {stock.price?.toLocaleString('en-IN')}</p>
                      <p className="font-mono">Change: {stock.change_pct}%</p>
                    </div>
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          </div>
        ))}
      </div>
    </TooltipProvider>
  );
}

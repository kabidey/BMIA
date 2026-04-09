import React from 'react';
import { Card, CardContent } from '../ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

export default function AlphaGauge({ alpha }) {
  if (!alpha) return null;

  const score = alpha.alpha_score || 0;
  const angle = (score / 100) * 180 - 90; // -90 to 90 degrees

  const getColor = (s) => {
    if (s > 85) return 'hsl(142, 70%, 45%)';
    if (s > 70) return 'hsl(142, 70%, 55%)';
    if (s > 60) return 'hsl(186, 92%, 42%)';
    if (s >= 40) return 'hsl(38, 92%, 55%)';
    if (s >= 30) return 'hsl(25, 90%, 55%)';
    return 'hsl(0, 72%, 52%)';
  };

  const gaugeColor = getColor(score);

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]" data-testid="alpha-score-gauge">
      <CardContent className="p-6 flex flex-col items-center">
        <p className="text-xs text-[hsl(var(--muted-foreground))] mb-3 font-medium">Alpha Score</p>
        
        {/* SVG Gauge */}
        <div className="relative w-48 h-28">
          <svg viewBox="0 0 200 110" className="w-full h-full">
            {/* Background arc */}
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              stroke="hsl(222, 14%, 16%)"
              strokeWidth="12"
              strokeLinecap="round"
            />
            {/* Score arc */}
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              stroke={gaugeColor}
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={`${(score / 100) * 251.2} 251.2`}
              style={{ transition: 'stroke-dasharray 0.8s ease-out' }}
            />
            {/* Threshold markers */}
            <line x1="55" y1="35" x2="55" y2="45" stroke="hsl(0, 72%, 52%)" strokeWidth="2" opacity="0.5" />
            <line x1="100" y1="18" x2="100" y2="28" stroke="hsl(38, 92%, 55%)" strokeWidth="2" opacity="0.5" />
            <line x1="155" y1="45" x2="155" y2="55" stroke="hsl(142, 70%, 45%)" strokeWidth="2" opacity="0.5" />
            {/* Labels */}
            <text x="15" y="108" fill="hsl(215, 16%, 50%)" fontSize="8" fontFamily="Azeret Mono">0</text>
            <text x="90" y="15" fill="hsl(215, 16%, 50%)" fontSize="8" fontFamily="Azeret Mono">50</text>
            <text x="175" y="108" fill="hsl(215, 16%, 50%)" fontSize="8" fontFamily="Azeret Mono">100</text>
          </svg>
          {/* Center score */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
            <p className="font-mono text-3xl font-bold tabular-nums" style={{ color: gaugeColor }} data-testid="alpha-score-value">
              {score.toFixed(1)}
            </p>
          </div>
        </div>

        {/* Recommendation */}
        <div className="mt-3 text-center">
          <span
            className="inline-block px-3 py-1 rounded-full text-sm font-semibold text-white"
            style={{ backgroundColor: alpha.recommendation_color }}
          >
            {alpha.recommendation}
          </span>
        </div>

        {/* Sub-scores */}
        <TooltipProvider>
          <div className="flex gap-4 mt-4 text-center">
            <Tooltip>
              <TooltipTrigger>
                <div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Tech</p>
                  <p className="font-mono text-sm font-bold tabular-nums">{alpha.technical_score}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent>Technical Score (40% weight)</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger>
                <div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Fund</p>
                  <p className="font-mono text-sm font-bold tabular-nums">{alpha.fundamental_score}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent>Fundamental Score (40% weight)</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger>
                <div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Sent</p>
                  <p className="font-mono text-sm font-bold tabular-nums">{alpha.sentiment_score}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent>Sentiment Score (20% weight)</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>

        {/* Sharpe */}
        {alpha.sharpe_ratio != null && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2 font-mono">
            Sharpe: {alpha.sharpe_ratio}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

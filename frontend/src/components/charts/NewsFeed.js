import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { ExternalLink } from 'lucide-react';

export default function NewsFeed({ news, sentiment }) {
  const headlines = news?.headlines || [];
  const perHeadline = sentiment?.per_headline || [];

  const getSentimentColor = (score) => {
    if (score > 0.3) return 'text-up';
    if (score < -0.3) return 'text-down';
    return 'text-neutral-color';
  };

  const getSentimentBg = (score) => {
    if (score > 0.3) return 'bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]';
    if (score < -0.3) return 'bg-[hsl(var(--danger))]/10 text-[hsl(var(--danger))]';
    return 'bg-[hsl(var(--muted))]/50 text-[hsl(var(--muted-foreground))]';
  };

  return (
    <div className="space-y-6">
      {/* Overall Sentiment */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Sentiment Score</p>
            <p className={`font-mono text-4xl font-bold tabular-nums mt-2 ${getSentimentColor(sentiment?.score || 0)}`}>
              {sentiment?.score?.toFixed(2) || '0.00'}
            </p>
            <Badge
              variant={sentiment?.label === 'Bullish' ? 'default' : sentiment?.label === 'Bearish' ? 'destructive' : 'secondary'}
              className="mt-2"
            >
              {sentiment?.label || 'Neutral'}
            </Badge>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2 bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6">
            <p className="text-xs text-[hsl(var(--muted-foreground))] mb-2">AI Analysis</p>
            <p className="text-sm text-[hsl(var(--foreground))] leading-relaxed">{sentiment?.rationale || 'No analysis available.'}</p>
            {sentiment?.keywords?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {sentiment.keywords.map((kw, i) => (
                  <Badge key={i} variant="outline" className="text-xs">{kw}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Headlines */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-display">News Headlines ({headlines.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px]">
            <div className="space-y-2">
              {headlines.map((h, i) => {
                const headlineSentiment = perHeadline.find(p => p.index === i + 1);
                return (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 rounded-lg bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] group"
                    style={{ transition: 'background-color 0.15s ease' }}
                  >
                    {headlineSentiment && (
                      <span className={`text-xs font-mono font-bold px-2 py-1 rounded ${getSentimentBg(headlineSentiment.score)}`}>
                        {headlineSentiment.score > 0 ? '+' : ''}{headlineSentiment.score.toFixed(1)}
                      </span>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium leading-snug">{h.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">{h.publisher}</span>
                        {h.date && <span className="text-xs text-[hsl(var(--muted-foreground))] font-mono">{h.date.slice(0, 10)}</span>}
                      </div>
                      {headlineSentiment?.brief && (
                        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 italic">{headlineSentiment.brief}</p>
                      )}
                    </div>
                    {h.link && (
                      <a href={h.link} target="_blank" rel="noopener noreferrer" className="opacity-0 group-hover:opacity-100">
                        <ExternalLink className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                      </a>
                    )}
                  </div>
                );
              })}
              {headlines.length === 0 && (
                <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">No headlines found for this symbol.</p>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

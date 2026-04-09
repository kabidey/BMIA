import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Zap, RefreshCw, Target, ShieldAlert, TrendingUp, TrendingDown, Clock, Brain, Loader2, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const ACTION_COLORS = {
  BUY: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  SELL: 'bg-red-500/10 text-red-400 border-red-500/30',
  HOLD: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  AVOID: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
};

const STATUS_COLORS = {
  OPEN: 'bg-blue-500/10 text-blue-400',
  HIT_TARGET: 'bg-emerald-500/10 text-emerald-400',
  HIT_STOP: 'bg-red-500/10 text-red-400',
  EXPIRED: 'bg-gray-500/10 text-gray-400',
};

export default function SignalDashboard() {
  const [activeSignals, setActiveSignals] = useState([]);
  const [historySignals, setHistorySignals] = useState([]);
  const [learningCtx, setLearningCtx] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const { getActiveSignals, getSignalHistory, evaluateAllSignals, getLearningContext } = useApi();
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const [active, history, learning] = await Promise.all([
        getActiveSignals(),
        getSignalHistory(50),
        getLearningContext(),
      ]);
      setActiveSignals(active.signals || []);
      setHistorySignals(history.signals || []);
      setLearningCtx(learning);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const handleEvaluateAll = async () => {
    setEvaluating(true);
    try {
      await evaluateAllSignals();
      await loadData();
    } catch (e) {
      console.error(e);
    }
    setEvaluating(false);
  };

  const formatPrice = (p) => p ? Number(p).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--';

  const SignalCard = ({ signal, showLiveReturn = false }) => {
    const liveReturn = signal.live_return_pct || signal.return_pct || 0;
    return (
      <div
        className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/30 cursor-pointer animate-fade-in"
        style={{ transition: 'border-color 0.2s ease' }}
        onClick={() => navigate(`/analyze/${encodeURIComponent(signal.symbol)}`)}
        data-testid={`signal-card-${signal.symbol}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-md text-xs font-bold border ${ACTION_COLORS[signal.action] || ACTION_COLORS.HOLD}`}>
              {signal.action}
            </span>
            <span className="font-mono text-sm font-bold">{signal.symbol?.replace('.NS', '').replace('=F', '')}</span>
            <Badge variant="outline" className="text-xs">{signal.timeframe}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLORS[signal.status] || ''}`}>
              {signal.status}
            </span>
            <span className="text-xs text-[hsl(var(--muted-foreground))]">C: {signal.confidence}%</span>
          </div>
        </div>

        {/* Price levels */}
        <div className="grid grid-cols-4 gap-3 mb-3">
          <div>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Entry</p>
            <p className="font-mono text-sm font-bold tabular-nums">{formatPrice(signal.entry_price || signal.entry?.price)}</p>
          </div>
          <div>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Target</p>
            <p className="font-mono text-sm font-bold tabular-nums text-emerald-400">
              {signal.targets?.[0]?.price ? formatPrice(signal.targets[0].price) : '--'}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Stop Loss</p>
            <p className="font-mono text-sm font-bold tabular-nums text-red-400">
              {formatPrice(signal.stop_loss?.price)}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">{showLiveReturn ? 'Live P&L' : 'Return'}</p>
            <p className={`font-mono text-sm font-bold tabular-nums ${liveReturn > 0 ? 'text-up' : liveReturn < 0 ? 'text-down' : 'text-neutral-color'}`}>
              {liveReturn > 0 ? '+' : ''}{liveReturn.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Theses */}
        {signal.key_theses && signal.key_theses.length > 0 && (
          <div className="mt-2">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase mb-1">Key Theses</p>
            <ul className="space-y-1">
              {signal.key_theses.slice(0, 2).map((t, i) => (
                <li key={i} className="text-xs text-[hsl(var(--foreground))]/80 flex gap-1.5">
                  <span className="text-[hsl(var(--primary))] mt-0.5">-</span>
                  <span className="line-clamp-2">{t}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-[hsl(var(--border))]/50">
          <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
            {signal.horizon_days}d horizon | RR: {signal.risk_reward_ratio || 'N/A'}
          </span>
          <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
            {signal.days_open || 0}d open | {signal.provider}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px]" data-testid="signal-dashboard-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-3">
            <Zap className="w-8 h-8 text-[hsl(var(--primary))]" />
            AI Signal Dashboard
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            AI-generated trade signals with real-time tracking & performance learning
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleEvaluateAll} disabled={evaluating} data-testid="evaluate-all-button">
            {evaluating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Evaluate All
          </Button>
          <Button onClick={() => navigate('/analyze')} data-testid="generate-signal-button">
            <Zap className="w-4 h-4 mr-2" /> Generate Signal
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Active Signals</p>
            <p className="font-mono text-3xl font-bold text-[hsl(var(--primary))] mt-1">{activeSignals.length}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Win Rate</p>
            <p className="font-mono text-3xl font-bold mt-1">{learningCtx?.win_rate != null ? `${learningCtx.win_rate}%` : '--'}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Total Signals</p>
            <p className="font-mono text-3xl font-bold mt-1">{learningCtx?.total_signals || historySignals.length}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Avg Return</p>
            <p className={`font-mono text-3xl font-bold mt-1 ${(learningCtx?.avg_return || 0) >= 0 ? 'text-up' : 'text-down'}`}>
              {learningCtx?.avg_return != null ? `${learningCtx.avg_return}%` : '--'}
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="active" className="space-y-4">
        <TabsList className="bg-[hsl(var(--surface-2))]">
          <TabsTrigger value="active" className="gap-2" data-testid="tab-active-signals">
            <Zap className="w-4 h-4" /> Active ({activeSignals.length})
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-2" data-testid="tab-history">
            <Clock className="w-4 h-4" /> History ({historySignals.length})
          </TabsTrigger>
          <TabsTrigger value="learning" className="gap-2" data-testid="tab-learning">
            <Brain className="w-4 h-4" /> AI Learning
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="space-y-4">
          {loading ? (
            Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)
          ) : activeSignals.length === 0 ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-12 text-center">
                <Zap className="w-16 h-16 text-[hsl(var(--muted-foreground))] mx-auto mb-4 opacity-20" />
                <h3 className="font-display text-xl font-semibold mb-2">No Active Signals</h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">Go to Symbol Analysis to generate your first AI signal</p>
                <Button onClick={() => navigate('/analyze')}>
                  <Zap className="w-4 h-4 mr-2" /> Generate Signal
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {activeSignals.map((sig) => <SignalCard key={sig._id} signal={sig} showLiveReturn={true} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          {loading ? (
            Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)
          ) : historySignals.length === 0 ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-12 text-center">
                <Clock className="w-16 h-16 text-[hsl(var(--muted-foreground))] mx-auto mb-4 opacity-20" />
                <p className="text-sm text-[hsl(var(--muted-foreground))]">No signal history yet</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {historySignals.map((sig) => <SignalCard key={sig._id} signal={sig} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="learning">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader>
              <CardTitle className="text-base font-display flex items-center gap-2">
                <Brain className="w-5 h-5 text-[hsl(var(--primary))]" />
                AI Learning Insights
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!learningCtx ? (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">No learning data yet.</p>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">Total Analyzed</p>
                      <p className="font-mono text-xl font-bold">{learningCtx.total_signals}</p>
                    </div>
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">Win Rate</p>
                      <p className="font-mono text-xl font-bold">{learningCtx.win_rate != null ? `${learningCtx.win_rate}%` : 'N/A'}</p>
                    </div>
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">BUY Win Rate</p>
                      <p className="font-mono text-xl font-bold">{learningCtx.buy_win_rate != null ? `${learningCtx.buy_win_rate}%` : 'N/A'}</p>
                    </div>
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">SELL Win Rate</p>
                      <p className="font-mono text-xl font-bold">{learningCtx.sell_win_rate != null ? `${learningCtx.sell_win_rate}%` : 'N/A'}</p>
                    </div>
                  </div>

                  {learningCtx.lessons && learningCtx.lessons.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold mb-2 text-[hsl(var(--primary))]">Lessons Learned</h4>
                      <div className="space-y-2">
                        {learningCtx.lessons.map((lesson, i) => (
                          <div key={i} className="flex gap-2 bg-[hsl(var(--surface-2))] rounded-lg p-3">
                            <Brain className="w-4 h-4 text-[hsl(var(--primary))] flex-shrink-0 mt-0.5" />
                            <p className="text-sm text-[hsl(var(--foreground))]/80">{lesson}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {learningCtx.recent_mistakes && learningCtx.recent_mistakes.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold mb-2 text-red-400">Recent Mistakes to Avoid</h4>
                      <div className="space-y-2">
                        {learningCtx.recent_mistakes.map((mistake, i) => (
                          <div key={i} className="flex gap-2 bg-red-500/5 border border-red-500/20 rounded-lg p-3">
                            <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                            <p className="text-sm text-[hsl(var(--foreground))]/80">{mistake}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
        <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
          <strong>SEBI Disclaimer:</strong> AI-generated signals are for educational purposes only. They do not constitute investment advice. Past performance does not guarantee future results. The AI learns from outcomes but cannot predict market movements with certainty. Always consult a SEBI-registered financial advisor.
        </p>
      </div>
    </div>
  );
}

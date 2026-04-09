import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import { Search, TrendingUp, BarChart3, FileText, MessageSquare, Loader2, AlertTriangle, Send, Zap, Target, ShieldAlert, Brain } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import AlphaGauge from '../components/charts/AlphaGauge';
import CandlestickChart from '../components/charts/CandlestickChart';
import RSIChart from '../components/charts/RSIChart';
import MACDChart from '../components/charts/MACDChart';
import FundamentalsPanel from '../components/charts/FundamentalsPanel';
import NewsFeed from '../components/charts/NewsFeed';
import FormulaDisplay from '../components/charts/FormulaDisplay';

const ACTION_COLORS = {
  BUY: 'bg-emerald-500 text-white',
  SELL: 'bg-red-500 text-white',
  HOLD: 'bg-amber-500 text-white',
  AVOID: 'bg-gray-500 text-white',
};

export default function SymbolAnalysis() {
  const { symbol: urlSymbol } = useParams();
  const navigate = useNavigate();
  const [symbol, setSymbol] = useState(urlSymbol || '');
  const [searchInput, setSearchInput] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatProvider, setChatProvider] = useState('openai');
  // Signal state
  const [signal, setSignal] = useState(null);
  const [signalLoading, setSignalLoading] = useState(false);
  const [signalProvider, setSignalProvider] = useState('openai');
  const { analyzeStock, aiChat, generateSignal } = useApi();

  const doAnalysis = useCallback(async (sym) => {
    if (!sym) return;
    setLoading(true);
    setAnalysis(null);
    setSignal(null);
    setLoadingStep('Fetching market data...');
    try {
      setTimeout(() => setLoadingStep('Computing technical indicators...'), 2000);
      setTimeout(() => setLoadingStep('Analyzing fundamentals...'), 4000);
      setTimeout(() => setLoadingStep('Scanning news sentiment...'), 6000);
      setTimeout(() => setLoadingStep('Computing Alpha Score...'), 8000);
      const data = await analyzeStock(sym);
      setAnalysis(data);
      setSymbol(sym);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
    setLoadingStep('');
  }, [analyzeStock]);

  useEffect(() => {
    if (urlSymbol) {
      doAnalysis(decodeURIComponent(urlSymbol));
    }
  }, [urlSymbol, doAnalysis]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchInput.trim()) {
      let sym = searchInput.trim().toUpperCase();
      if (!sym.includes('.') && !sym.includes('=')) {
        sym = sym + '.NS';
      }
      navigate(`/analyze/${encodeURIComponent(sym)}`);
    }
  };

  const handleGenerateSignal = async () => {
    if (!symbol) return;
    setSignalLoading(true);
    try {
      const result = await generateSignal(symbol, signalProvider);
      setSignal(result);
    } catch (e) {
      console.error(e);
    }
    setSignalLoading(false);
  };

  const handleChat = async () => {
    if (!chatInput.trim() || !symbol) return;
    const userMsg = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatLoading(true);
    try {
      const result = await aiChat(symbol, userMsg, chatProvider, analysis ? {
        market: analysis.market_data,
        technical: { score: analysis.technical?.technical_score, rsi: analysis.technical?.rsi?.current },
        fundamental: analysis.fundamental,
        alpha: analysis.alpha,
      } : null);
      setChatMessages(prev => [...prev, { role: 'assistant', content: result.response, provider: result.provider }]);
    } catch (e) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    }
    setChatLoading(false);
  };

  const formatPrice = (p) => p ? p.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--';

  return (
    <div className="p-6 space-y-6 max-w-[1600px]" data-testid="symbol-analysis-page">
      {/* Search Bar */}
      <div className="flex items-center gap-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
            <Input
              data-testid="symbol-search-input"
              placeholder="Enter symbol (e.g., RELIANCE, TCS, GC=F)"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-10 bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]"
            />
          </div>
          <Button type="submit" disabled={loading} data-testid="analyze-button">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Analyze'}
          </Button>
        </form>
      </div>

      {/* Loading State */}
      {loading && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-8">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="w-10 h-10 animate-spin text-[hsl(var(--primary))]" />
              <p className="text-sm font-medium text-[hsl(var(--primary))] animate-pulse-glow">{loadingStep}</p>
              <div className="w-64 space-y-2">
                {['Fetching market data', 'Computing indicators', 'Analyzing fundamentals', 'Scoring sentiment', 'Computing Alpha'].map((step) => (
                  <div key={step} className={`loading-step ${loadingStep.toLowerCase().includes(step.split(' ')[0].toLowerCase()) ? 'active' : ''}`}>
                    <div className={`w-2 h-2 rounded-full ${
                      loadingStep.toLowerCase().includes(step.split(' ')[0].toLowerCase()) ? 'bg-[hsl(var(--primary))] animate-pulse-glow' : 'bg-[hsl(var(--muted))]'
                    }`} />
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analysis Results */}
      {analysis && !loading && (
        <>
          {/* Header with Alpha Score */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="font-display text-2xl font-bold">
                        {analysis.symbol_info?.name || analysis.symbol}
                      </h2>
                      <Badge variant="secondary" className="font-mono">
                        {analysis.symbol?.replace('.NS', '').replace('=F', '')}
                      </Badge>
                      <Badge variant="outline">{analysis.symbol_info?.sector || analysis.fundamental?.sector}</Badge>
                    </div>
                    <div className="flex items-baseline gap-4 mt-3">
                      <span className="font-mono text-3xl font-bold tabular-nums" data-testid="stock-price">
                        {formatPrice(analysis.market_data?.latest?.close)}
                      </span>
                      <span className={`font-mono text-lg tabular-nums ${analysis.market_data?.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                        {analysis.market_data?.change >= 0 ? '+' : ''}{analysis.market_data?.change}
                        ({analysis.market_data?.change_pct >= 0 ? '+' : ''}{analysis.market_data?.change_pct}%)
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge
                      style={{ backgroundColor: analysis.alpha?.recommendation_color, color: '#fff' }}
                      className="text-sm px-3 py-1"
                      data-testid="recommendation-badge"
                    >
                      {analysis.alpha?.recommendation}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
            <AlphaGauge alpha={analysis.alpha} />
          </div>

          {/* AI Signal Generation Section */}
          <Card className="bg-gradient-to-r from-[hsl(var(--surface-1))] to-[hsl(var(--surface-2))] border-[hsl(var(--primary))]/30 border" data-testid="signal-generation-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary))]/20 flex items-center justify-center">
                    <Zap className="w-6 h-6 text-[hsl(var(--primary))]" />
                  </div>
                  <div>
                    <h3 className="font-display font-semibold">AI Intelligence Engine</h3>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Multi-input signal generation with learning from past outcomes</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    {['openai', 'claude', 'gemini'].map((p) => (
                      <Button
                        key={p}
                        variant={signalProvider === p ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSignalProvider(p)}
                        className="text-xs capitalize"
                      >
                        {p}
                      </Button>
                    ))}
                  </div>
                  <Button
                    onClick={handleGenerateSignal}
                    disabled={signalLoading}
                    className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90"
                    data-testid="generate-signal-button"
                  >
                    {signalLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4 mr-2" />
                        Generate AI Signal
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Signal Loading */}
              {signalLoading && (
                <div className="bg-[hsl(var(--surface-2))] rounded-lg p-6 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--primary))] mx-auto mb-3" />
                  <p className="text-sm text-[hsl(var(--primary))]">Intelligence engine processing all data sources...</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Technical + Fundamental + Sentiment + Learning Context</p>
                </div>
              )}

              {/* Signal Result */}
              {signal && !signalLoading && (
                <div className="space-y-4 animate-fade-in" data-testid="signal-result">
                  {/* Action Banner */}
                  <div className={`rounded-lg p-4 flex items-center justify-between ${ACTION_COLORS[signal.signal?.action] || 'bg-gray-500 text-white'}`}>
                    <div className="flex items-center gap-3">
                      {signal.signal?.action === 'BUY' && <TrendingUp className="w-6 h-6" />}
                      {signal.signal?.action === 'SELL' && <TrendingUp className="w-6 h-6 rotate-180" />}
                      {signal.signal?.action === 'HOLD' && <ShieldAlert className="w-6 h-6" />}
                      {signal.signal?.action === 'AVOID' && <AlertTriangle className="w-6 h-6" />}
                      <div>
                        <p className="text-xl font-display font-bold">{signal.signal?.action} Signal</p>
                        <p className="text-sm opacity-90">{signal.signal?.timeframe} | {signal.signal?.horizon_days}d horizon</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-mono font-bold">{signal.signal?.confidence}%</p>
                      <p className="text-xs opacity-80">confidence</p>
                    </div>
                  </div>

                  {/* Price Levels */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-[hsl(var(--border))]">
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Entry Price</p>
                      <p className="font-mono text-lg font-bold tabular-nums">{formatPrice(signal.signal?.entry?.price)}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">{signal.signal?.entry?.rationale?.slice(0, 80)}</p>
                    </div>
                    {signal.signal?.targets?.map((t, i) => (
                      <div key={i} className="bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-emerald-500/20">
                        <p className="text-[10px] text-emerald-400 uppercase">{t.label}</p>
                        <p className="font-mono text-lg font-bold tabular-nums text-emerald-400">{formatPrice(t.price)}</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Probability: {(t.probability * 100).toFixed(0)}%</p>
                      </div>
                    ))}
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-red-500/20">
                      <p className="text-[10px] text-red-400 uppercase">Stop Loss ({signal.signal?.stop_loss?.type})</p>
                      <p className="font-mono text-lg font-bold tabular-nums text-red-400">{formatPrice(signal.signal?.stop_loss?.price)}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">{signal.signal?.stop_loss?.rationale?.slice(0, 80)}</p>
                    </div>
                  </div>

                  {/* RR + Position + Sector */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Risk/Reward</p>
                      <p className="font-mono text-sm font-bold">{signal.signal?.risk_reward_ratio}</p>
                    </div>
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Position Sizing</p>
                      <p className="text-xs font-medium">{signal.signal?.position_sizing_hint}</p>
                    </div>
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase">Sector Context</p>
                      <p className="text-xs font-medium line-clamp-2">{signal.signal?.sector_context}</p>
                    </div>
                  </div>

                  {/* Key Theses */}
                  <div className="bg-[hsl(var(--surface-2))] rounded-lg p-4">
                    <p className="text-xs font-semibold text-[hsl(var(--primary))] mb-2 uppercase">Key Theses</p>
                    <ul className="space-y-2">
                      {signal.signal?.key_theses?.map((thesis, i) => (
                        <li key={i} className="flex gap-2 text-sm">
                          <Target className="w-4 h-4 text-[hsl(var(--primary))] flex-shrink-0 mt-0.5" />
                          <span>{thesis}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Invalidators */}
                  {signal.signal?.invalidators?.length > 0 && (
                    <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
                      <p className="text-xs font-semibold text-red-400 mb-2 uppercase">What Would Prove This Wrong</p>
                      <ul className="space-y-2">
                        {signal.signal.invalidators.map((inv, i) => (
                          <li key={i} className="flex gap-2 text-sm">
                            <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                            <span className="text-[hsl(var(--foreground))]/80">{inv}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Detailed Reasoning */}
                  <div className="bg-[hsl(var(--surface-2))] rounded-lg p-4">
                    <p className="text-xs font-semibold text-[hsl(var(--primary))] mb-2 uppercase flex items-center gap-1">
                      <Brain className="w-4 h-4" /> Detailed AI Reasoning
                    </p>
                    <p className="text-sm text-[hsl(var(--foreground))]/80 leading-relaxed whitespace-pre-line">
                      {signal.signal?.detailed_reasoning}
                    </p>
                  </div>

                  {/* Learning Context */}
                  {signal.learning_context_summary && (
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 flex items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
                      <Brain className="w-4 h-4 text-[hsl(var(--primary))]" />
                      <span>Past signals: {signal.learning_context_summary.total_past_signals}</span>
                      {signal.learning_context_summary.win_rate != null && (
                        <span>Win rate: {signal.learning_context_summary.win_rate}%</span>
                      )}
                      <span>Lessons applied: {signal.learning_context_summary.lessons_count}</span>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tabbed Content */}
          <Tabs defaultValue="technical" className="space-y-4">
            <TabsList className="bg-[hsl(var(--surface-2))]">
              <TabsTrigger value="technical" className="gap-2" data-testid="tab-technical">
                <BarChart3 className="w-4 h-4" /> Technical
              </TabsTrigger>
              <TabsTrigger value="fundamental" className="gap-2" data-testid="tab-fundamental">
                <FileText className="w-4 h-4" /> Fundamental
              </TabsTrigger>
              <TabsTrigger value="news" className="gap-2" data-testid="tab-news">
                <FileText className="w-4 h-4" /> News & Sentiment
              </TabsTrigger>
              <TabsTrigger value="ai" className="gap-2" data-testid="tab-ai">
                <MessageSquare className="w-4 h-4" /> AI Agent
              </TabsTrigger>
              <TabsTrigger value="formulas" className="gap-2" data-testid="tab-formulas">
                <TrendingUp className="w-4 h-4" /> Formulas
              </TabsTrigger>
            </TabsList>

            {/* Technical Tab */}
            <TabsContent value="technical" className="space-y-6">
              <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">RSI (14)</p>
                    <p className="font-mono text-2xl font-bold tabular-nums mt-1" data-testid="rsi-value">
                      {analysis.technical?.rsi?.current?.toFixed(2) || '--'}
                    </p>
                    <Badge variant={analysis.technical?.rsi?.current > 70 ? 'destructive' : analysis.technical?.rsi?.current < 30 ? 'default' : 'secondary'} className="mt-1">
                      {analysis.technical?.rsi?.current > 70 ? 'Overbought' : analysis.technical?.rsi?.current < 30 ? 'Oversold' : 'Normal'}
                    </Badge>
                  </CardContent>
                </Card>
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">MACD Histogram</p>
                    <p className={`font-mono text-2xl font-bold tabular-nums mt-1 ${analysis.technical?.macd?.histogram > 0 ? 'text-up' : 'text-down'}`}>
                      {analysis.technical?.macd?.histogram?.toFixed(4) || '--'}
                    </p>
                    <Badge variant={analysis.technical?.macd?.histogram > 0 ? 'default' : 'destructive'} className="mt-1">
                      {analysis.technical?.macd?.histogram > 0 ? 'Bullish' : 'Bearish'}
                    </Badge>
                  </CardContent>
                </Card>
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">VSA Signal</p>
                    <p className="font-mono text-lg font-bold mt-1">{analysis.technical?.vsa?.signal || '--'}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Vol Ratio: {analysis.technical?.vsa?.vol_ratio || '--'}</p>
                  </CardContent>
                </Card>
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Technical Score</p>
                    <p className="font-mono text-2xl font-bold tabular-nums mt-1 text-[hsl(var(--primary))]" data-testid="technical-score">
                      {analysis.technical?.technical_score || '--'}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
                      Breakout: {analysis.technical?.breakout?.is_breakout ? 'Yes' : 'No'}
                    </p>
                  </CardContent>
                </Card>
              </div>

              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-display">Price Chart (Candlestick + Volume)</CardTitle>
                </CardHeader>
                <CardContent data-testid="candlestick-chart-container">
                  <CandlestickChart data={analysis.chart_data?.ohlcv || []} />
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-display">RSI (14)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RSIChart data={analysis.chart_data?.rsi || []} />
                  </CardContent>
                </Card>
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-display">MACD (12, 26, 9)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <MACDChart data={analysis.chart_data?.macd || []} />
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Fundamental Tab */}
            <TabsContent value="fundamental">
              <FundamentalsPanel data={analysis.fundamental} />
            </TabsContent>

            {/* News Tab */}
            <TabsContent value="news">
              <NewsFeed news={analysis.news} sentiment={analysis.sentiment} />
            </TabsContent>

            {/* AI Agent Tab */}
            <TabsContent value="ai">
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-display">AI Market Analyst</CardTitle>
                    <div className="flex gap-1">
                      {['openai', 'claude', 'gemini'].map((p) => (
                        <Button
                          key={p}
                          variant={chatProvider === p ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setChatProvider(p)}
                          className="text-xs capitalize"
                          data-testid={`provider-${p}`}
                        >
                          {p}
                        </Button>
                      ))}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--warning))]/20 rounded-lg p-3 mb-4 flex gap-2">
                    <AlertTriangle className="w-4 h-4 text-[hsl(var(--warning))] flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      AI analysis is for educational purposes only. Not financial advice.
                    </p>
                  </div>

                  <ScrollArea className="h-[400px] pr-4 mb-4">
                    <div className="space-y-4">
                      {chatMessages.length === 0 && (
                        <div className="text-center py-12">
                          <MessageSquare className="w-12 h-12 text-[hsl(var(--muted-foreground))] mx-auto mb-3 opacity-30" />
                          <p className="text-sm text-[hsl(var(--muted-foreground))]">Ask the AI agent about {symbol.replace('.NS', '')}</p>
                          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">e.g., "What are the key risks?" or "Should I buy at current levels?"</p>
                        </div>
                      )}
                      {chatMessages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] rounded-lg p-3 text-sm ${
                            msg.role === 'user'
                              ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                              : 'bg-[hsl(var(--surface-2))] border-l-2 border-[hsl(var(--primary))]'
                          }`}>
                            <p className="whitespace-pre-wrap">{msg.content}</p>
                            {msg.provider && <p className="text-xs opacity-60 mt-2 capitalize">via {msg.provider}</p>}
                          </div>
                        </div>
                      ))}
                      {chatLoading && (
                        <div className="flex justify-start">
                          <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--primary))]" />
                            <span className="text-sm text-[hsl(var(--muted-foreground))]">Analyzing...</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </ScrollArea>

                  <div className="flex gap-2">
                    <Input
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask about this stock..."
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleChat()}
                      className="bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]"
                      data-testid="ai-chat-input"
                    />
                    <Button onClick={handleChat} disabled={chatLoading || !chatInput.trim()} data-testid="ai-chat-send-button">
                      <Send className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Formulas Tab */}
            <TabsContent value="formulas">
              <FormulaDisplay alpha={analysis.alpha} />
            </TabsContent>
          </Tabs>

          {/* Bottom Disclaimer */}
          <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
            <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
              <strong>SEBI Disclaimer:</strong> {analysis.alpha?.disclaimer}
            </p>
          </div>
        </>
      )}

      {/* Empty State */}
      {!analysis && !loading && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-12 text-center">
            <Zap className="w-16 h-16 text-[hsl(var(--muted-foreground))] mx-auto mb-4 opacity-20" />
            <h3 className="font-display text-xl font-semibold mb-2">Analyze Any Stock or Commodity</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
              Enter a symbol above to get AI-powered multi-input analysis with actionable signals
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'GC=F', 'INFY.NS'].map((s) => (
                <Button
                  key={s}
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/analyze/${encodeURIComponent(s)}`)}
                  className="font-mono"
                >
                  {s.replace('.NS', '').replace('=F', '')}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

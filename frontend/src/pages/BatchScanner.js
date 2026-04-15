import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Progress } from '../components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Loader2, ArrowUpDown, Brain, Zap, TrendingUp, TrendingDown, Minus,
  AlertTriangle, Layers, Shield, Eye, CheckCircle, XCircle, MinusCircle,
  Sparkles, BarChart3, Filter, History, Clock
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const ACTION_STYLES = {
  BUY: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', icon: TrendingUp },
  SELL: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', icon: TrendingDown },
  HOLD: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', icon: Minus },
  AVOID: { bg: 'bg-gray-500/15', text: 'text-gray-400', border: 'border-gray-500/30', icon: AlertTriangle },
};

const AGREEMENT_STYLES = {
  HIGH: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: CheckCircle },
  MEDIUM: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', icon: MinusCircle },
  LOW: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: XCircle },
};

function ModelVoteBadge({ provider, action }) {
  const colors = {
    openai: 'border-emerald-500/40 text-emerald-400',
    claude: 'border-violet-500/40 text-violet-400',
    gemini: 'border-blue-500/40 text-blue-400',
  };
  const labels = { openai: 'GPT', claude: 'Claude', gemini: 'Gemini' };
  const actionColor = action === 'BUY' ? 'bg-emerald-500/20' : action === 'SELL' ? 'bg-red-500/20' : 'bg-gray-500/20';

  return (
    <Badge variant="outline" className={`text-[9px] px-1.5 py-0 ${colors[provider] || ''} ${actionColor}`}>
      {labels[provider] || provider}: {action || '?'}
    </Badge>
  );
}

function PipelineTracker({ pipeline, isRunning }) {
  if (!pipeline && !isRunning) return null;

  const stages = [
    { key: 'universe', label: 'Universe', desc: 'Loading 3400+ NSE + BSE stocks', icon: Layers },
    { key: 'prefilter', label: 'Pre-Filter', desc: 'Quantitative screening', icon: Filter },
    { key: 'shortlist', label: 'Shortlist', desc: 'Deep feature computation', icon: BarChart3 },
    { key: 'god_mode', label: 'God Mode', desc: '3-LLM ensemble analysis', icon: Sparkles },
    { key: 'complete', label: 'Complete', desc: 'Distilled results ready', icon: CheckCircle },
  ];

  const currentIdx = stages.findIndex(s => s.key === (pipeline?.stage || (isRunning ? 'universe' : 'complete')));

  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--primary))]/20">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-[hsl(var(--primary))]" />
          <span className="text-sm font-display font-semibold">God Mode Pipeline</span>
          {pipeline?.universe_size && (
            <Badge variant="secondary" className="text-[10px]">{pipeline.universe_size} stocks scanned</Badge>
          )}
          {pipeline?.candidates && (
            <Badge variant="secondary" className="text-[10px]">{pipeline.candidates} candidates</Badge>
          )}
          {pipeline?.shortlist_size && (
            <Badge variant="secondary" className="text-[10px]">{pipeline.shortlist_size} shortlisted</Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          {stages.map((stage, i) => {
            const isActive = i === currentIdx;
            const isDone = i < currentIdx || pipeline?.stage === 'complete';
            const StageIcon = stage.icon;
            return (
              <React.Fragment key={stage.key}>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium ${
                        isDone ? 'bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]' :
                        isActive ? 'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] animate-pulse' :
                        'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
                      }`} style={{ transition: 'all 0.3s ease' }}>
                        <StageIcon className={`w-3.5 h-3.5 ${isActive ? 'animate-spin' : ''}`} />
                        {stage.label}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent><p>{stage.desc}</p></TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {i < stages.length - 1 && (
                  <div className={`w-6 h-0.5 rounded ${isDone ? 'bg-[hsl(var(--primary))]' : 'bg-[hsl(var(--surface-3))]'}`}
                    style={{ transition: 'background-color 0.3s ease' }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function ScannerHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${BACKEND_URL}/api/batch/scan-history?limit=10`);
        const d = await res.json();
        setHistory(d.scans || []);
      } catch (e) { console.error(e); }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return null;
  if (history.length === 0) return null;

  return (
    <div data-testid="scanner-history-section">
      <div className="flex items-center gap-2 mb-3">
        <History className="w-4 h-4 text-[hsl(var(--primary))]" />
        <h2 className="text-base font-display font-bold text-[hsl(var(--foreground))]">Scan History</h2>
        <span className="text-[10px] bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] px-2 py-0.5 rounded">{history.length} past scans</span>
      </div>
      <div className="space-y-3">
        {history.map((scan, idx) => {
          const isOpen = expanded === idx;
          const buyCount = (scan.results_summary || []).filter(r => r.action === 'BUY').length;
          const date = new Date(scan.scanned_at);
          const dateStr = date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

          return (
            <Card key={scan.scan_id || idx} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] overflow-hidden" data-testid={`scan-history-${scan.scan_id || idx}`}>
              <div className="p-3 cursor-pointer hover:bg-[hsl(var(--surface-2))]" style={{ transition: 'background 0.15s' }}
                onClick={() => setExpanded(isOpen ? null : idx)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Clock className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />
                    <span className="text-xs font-mono text-[hsl(var(--foreground))]">{dateStr}</span>
                    {scan.god_mode && <Badge className="bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))] text-[9px]">God Mode</Badge>}
                    <Badge variant="secondary" className="text-[9px]">{scan.total_results} analyzed</Badge>
                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[9px]">{buyCount} BUY</Badge>
                    {scan.models_succeeded?.length > 0 && (
                      <span className="text-[9px] text-[hsl(var(--muted-foreground))] font-mono">{scan.models_succeeded.join(', ')}</span>
                    )}
                  </div>
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{isOpen ? 'Collapse' : 'Expand'}</span>
                </div>
              </div>
              {isOpen && (
                <div className="border-t border-[hsl(var(--border))] p-3">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-[10px] text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
                        <th className="py-1.5 px-2 text-left">Rank</th>
                        <th className="py-1.5 px-2 text-left">Symbol</th>
                        <th className="py-1.5 px-2 text-left">Sector</th>
                        <th className="py-1.5 px-2 text-right">Price</th>
                        <th className="py-1.5 px-2 text-right">Chg%</th>
                        <th className="py-1.5 px-2 text-center">AI</th>
                        <th className="py-1.5 px-2 text-center">Action</th>
                        <th className="py-1.5 px-2 text-left">Rationale</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(scan.results_summary || []).map((r, ri) => (
                        <tr key={ri} className="border-b border-[hsl(var(--border))]/30">
                          <td className="py-1.5 px-2 font-mono text-[hsl(var(--primary))]">#{r.rank}</td>
                          <td className="py-1.5 px-2 font-mono font-medium">{(r.name || r.symbol || '').replace('.NS', '')}</td>
                          <td className="py-1.5 px-2"><Badge variant="secondary" className="text-[9px]">{r.sector || 'N/A'}</Badge></td>
                          <td className="py-1.5 px-2 text-right font-mono">{r.price?.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</td>
                          <td className={`py-1.5 px-2 text-right font-mono ${(r.change_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {(r.change_pct || 0) >= 0 ? '+' : ''}{r.change_pct?.toFixed(2)}%
                          </td>
                          <td className="py-1.5 px-2 text-center font-mono font-bold">{r.ai_score ?? '--'}</td>
                          <td className="py-1.5 px-2 text-center">
                            <span className={`text-[9px] px-1.5 py-0.5 rounded ${r.action === 'BUY' ? 'bg-emerald-500/15 text-emerald-400' : r.action === 'SELL' ? 'bg-red-500/15 text-red-400' : 'bg-gray-500/15 text-gray-400'}`}>
                              {r.action}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-[hsl(var(--muted-foreground))] truncate max-w-[200px]">{r.rationale || '--'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default function BatchScanner() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [scanMeta, setScanMeta] = useState(null);
  const [sortField, setSortField] = useState('rank');
  const [sortDir, setSortDir] = useState('asc');
  const navigate = useNavigate();

  const runGodScan = async () => {
    setLoading(true);
    setResults([]);
    setError(null);
    setPipeline({ stage: 'universe' });

    try {
      // Step 1: Start the scan (returns immediately with job_id)
      const startRes = await fetch(`${BACKEND_URL}/api/batch/god-scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ market: 'NSE', max_candidates: 50, max_shortlist: 10, top_n: 10 }),
      });
      const startData = await startRes.json();

      if (!startData.job_id) {
        throw new Error(startData.error || 'Failed to start scan');
      }

      const jobId = startData.job_id;

      // Step 2: Realistic pipeline stage tracking
      const stageTimings = [
        { stage: 'universe', delay: 3000, extra: { universe_size: 2400 } },
        { stage: 'prefilter', delay: 8000, extra: { candidates: 50 } },
        { stage: 'shortlist', delay: 25000, extra: { shortlist_size: 10 } },
        { stage: 'god_mode', delay: 45000, extra: {} },
      ];
      let stageIdx = 0;
      const stageTimer = setInterval(() => {
        if (stageIdx < stageTimings.length) {
          setPipeline(p => ({ ...p, ...stageTimings[stageIdx].extra, stage: stageTimings[stageIdx].stage }));
          stageIdx++;
        }
      }, 15000);

      // Step 3: Poll for results (3.5 min max — matches backend hard timeout)
      let attempts = 0;
      const maxAttempts = 70;
      while (attempts < maxAttempts) {
        await new Promise(r => setTimeout(r, 3000));
        attempts++;

        try {
          const pollRes = await fetch(`${BACKEND_URL}/api/batch/god-scan/${jobId}`);
          const pollData = await pollRes.json();

          if (pollData.status === 'complete') {
            clearInterval(stageTimer);
            setResults(pollData.results || []);
            setPipeline(pollData.pipeline || { stage: 'complete' });
            setScanMeta({
              god_mode: pollData.god_mode,
              models_succeeded: pollData.models_succeeded || [],
              total: pollData.total,
              generated_at: pollData.generated_at,
              pipeline: pollData.pipeline,
            });
            setLoading(false);
            return;
          }

          if (pollData.status === 'error') {
            clearInterval(stageTimer);
            setError(pollData.error || 'Scan failed');
            setPipeline({ stage: 'complete' });
            setLoading(false);
            return;
          }
        } catch (pollErr) {
          console.warn('Poll failed, retrying...', pollErr);
        }
      }

      clearInterval(stageTimer);
      setError('Scan timed out after 3.5 minutes. The backend has a hard timeout to prevent infinite runs. Try again.');
      setPipeline({ stage: 'complete' });
    } catch (e) {
      console.error('God scan error:', e);
      setError(e.message || 'Failed to start scan');
      setPipeline({ stage: 'complete' });
    }
    setLoading(false);
  };

  // Don't auto-scan on mount - let user trigger it

  const sorted = [...results].sort((a, b) => {
    const aVal = a[sortField] ?? 999;
    const bVal = b[sortField] ?? 999;
    if (typeof aVal === 'string') return sortDir === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const toggleSort = (field) => {
    if (sortField === field) setSortDir(prev => prev === 'desc' ? 'asc' : 'desc');
    else { setSortField(field); setSortDir(field === 'rank' ? 'asc' : 'desc'); }
  };

  const SortHeader = ({ field, children, className = '' }) => (
    <th className={`py-3 px-2 font-medium cursor-pointer hover:text-[hsl(var(--foreground))] ${className}`}
      style={{ transition: 'color 0.15s ease' }} onClick={() => toggleSort(field)}>
      <span className="flex items-center gap-1">
        {children}
        <ArrowUpDown className={`w-3 h-3 ${sortField === field ? 'text-[hsl(var(--primary))]' : ''}`} />
      </span>
    </th>
  );

  // Count buy calls
  const buyCount = results.filter(r => r.action === 'BUY').length;
  const highAgreement = results.filter(r => r.agreement_level === 'HIGH').length;

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-[1920px]" data-testid="batch-scanner-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[hsl(var(--primary))]/30 to-violet-500/20 flex items-center justify-center border border-[hsl(var(--primary))]/20">
              <Sparkles className="w-7 h-7 text-[hsl(var(--primary))]" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold tracking-tight" data-testid="scanner-title">
                God Mode Scanner
              </h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
                Full-market scan &bull; 3400+ NSE + BSE stocks &bull; 3-LLM ensemble consensus &bull; Distilled BUY calls
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={runGodScan} disabled={loading} size="lg"
            className="bg-gradient-to-r from-[hsl(var(--primary))] to-violet-600 hover:opacity-90"
            data-testid="scan-button">
            {loading ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : <Sparkles className="w-5 h-5 mr-2" />}
            {loading ? 'Scanning...' : 'Launch God Scan'}
          </Button>
        </div>
      </div>

      {/* Pipeline Tracker */}
      <PipelineTracker pipeline={pipeline} isRunning={loading} />

      {/* Stats Row */}
      {!loading && results.length > 0 && (
        <div className="flex items-center gap-3 flex-wrap">
          <Badge variant="outline" className="text-xs gap-1.5 py-1 px-3 border-[hsl(var(--primary))]/30">
            <Sparkles className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
            God Mode Active
          </Badge>
          {scanMeta?.models_succeeded?.map(m => (
            <Badge key={m} variant="outline" className="text-[10px] py-0.5 capitalize">{m}</Badge>
          ))}
          <Badge variant="secondary" className="text-xs">{results.length} analyzed</Badge>
          <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">{buyCount} BUY calls</Badge>
          <Badge className="bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))] text-xs">{highAgreement} high agreement</Badge>
          {scanMeta?.pipeline?.universe_size && (
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
              {scanMeta.pipeline.universe_size} scanned → {scanMeta.pipeline.candidates} candidates → {scanMeta.pipeline.shortlist_size} shortlisted
            </span>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-8">
            <div className="flex flex-col items-center gap-5">
              <div className="relative">
                <div className="w-20 h-20 rounded-full border-4 border-[hsl(var(--primary))]/20 flex items-center justify-center">
                  <Sparkles className="w-10 h-10 text-[hsl(var(--primary))] animate-pulse" />
                </div>
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full animate-ping opacity-50" />
                <div className="absolute -bottom-1 -left-1 w-5 h-5 bg-violet-500 rounded-full animate-ping opacity-50" style={{ animationDelay: '0.5s' }} />
                <div className="absolute -top-1 -left-1 w-5 h-5 bg-blue-500 rounded-full animate-ping opacity-50" style={{ animationDelay: '1s' }} />
              </div>
              <div className="text-center">
                <p className="text-base font-display font-semibold">God Mode Activated</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
                  Scanning full NSE + BSE universe, filtering candidates, running 3-LLM ensemble...
                </p>
              </div>
              <div className="flex gap-3">
                {['GPT-4.1', 'Claude Sonnet', 'Gemini Flash'].map((m, i) => (
                  <Badge key={m} variant="outline" className="text-[10px] animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>
                    {m}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Table */}
      {!loading && results.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="scanner-table">
                <thead>
                  <tr className="border-b border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] text-left">
                    <SortHeader field="rank">Rank</SortHeader>
                    <th className="py-3 px-2 font-medium">Symbol</th>
                    <th className="py-3 px-2 font-medium">Sector</th>
                    <SortHeader field="price">Price</SortHeader>
                    <SortHeader field="change_pct">Chg %</SortHeader>
                    <SortHeader field="ai_score">AI Score</SortHeader>
                    <th className="py-3 px-2 font-medium">Action</th>
                    <th className="py-3 px-2 font-medium">Agreement</th>
                    <th className="py-3 px-2 font-medium">Model Votes</th>
                    <SortHeader field="vol_ratio">Vol xAvg</SortHeader>
                    <th className="py-3 px-2 font-medium min-w-[250px]">Distilled Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((stock) => {
                    const actionStyle = ACTION_STYLES[stock.action] || ACTION_STYLES.HOLD;
                    const agreeStyle = AGREEMENT_STYLES[stock.agreement_level] || AGREEMENT_STYLES.LOW;
                    const ActionIcon = actionStyle.icon;
                    const AgreeIcon = agreeStyle.icon;

                    return (
                      <tr key={stock.symbol}
                        className="border-b border-[hsl(var(--border))]/50 hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                        style={{ transition: 'background-color 0.15s ease' }}
                        onClick={() => navigate(`/analyze/${encodeURIComponent(stock.symbol)}`)}
                        data-testid={`scanner-row-${stock.symbol}`}>
                        <td className="py-3 px-2">
                          <span className="font-mono font-bold text-[hsl(var(--primary))] tabular-nums">
                            #{stock.rank || '-'}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <div>
                            <p className="font-mono font-medium tracking-wide">{stock.name || stock.symbol?.replace('.NS', '')}</p>
                            <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">{stock.symbol?.replace('.NS', '')}</p>
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <Badge variant="secondary" className="text-[10px]">{stock.sector || 'N/A'}</Badge>
                        </td>
                        <td className="py-3 px-2 font-mono tabular-nums text-right">
                          {stock.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                        </td>
                        <td className={`py-3 px-2 font-mono tabular-nums text-right ${(stock.change_pct || 0) >= 0 ? 'text-[hsl(var(--up))]' : 'text-[hsl(var(--down))]'}`}>
                          {(stock.change_pct || 0) >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2) || '0.00'}%
                        </td>
                        <td className="py-3 px-2 text-center">
                          {stock.ai_score != null ? (
                            <span className={`font-mono text-lg font-bold tabular-nums ${
                              stock.ai_score >= 70 ? 'text-[hsl(var(--up))]' :
                              stock.ai_score >= 40 ? 'text-amber-400' : 'text-[hsl(var(--down))]'
                            }`} data-testid="ai-score-value">
                              {stock.ai_score}
                            </span>
                          ) : <span className="text-[hsl(var(--muted-foreground))]">--</span>}
                        </td>
                        <td className="py-3 px-2">
                          <Badge className={`${actionStyle.bg} ${actionStyle.text} ${actionStyle.border} border text-xs gap-1`}>
                            <ActionIcon className="w-3 h-3" />
                            {stock.action || 'N/A'}
                          </Badge>
                        </td>
                        <td className="py-3 px-2">
                          <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${agreeStyle.bg} ${agreeStyle.color} ${agreeStyle.border}`}>
                            <AgreeIcon className="w-3 h-3" />
                            {stock.agreement_level || 'N/A'}
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex gap-1 flex-wrap">
                            {stock.model_votes && typeof stock.model_votes === 'object' &&
                              Object.entries(stock.model_votes).map(([prov, action]) => (
                                <ModelVoteBadge key={prov} provider={prov} action={typeof action === 'string' ? action : action?.action || action} />
                              ))
                            }
                          </div>
                        </td>
                        <td className="py-3 px-2 font-mono tabular-nums text-right">
                          {stock.vol_ratio ? (
                            <Badge variant={stock.vol_ratio >= 3 ? 'default' : 'secondary'} className="text-[10px]">
                              {stock.vol_ratio}x
                            </Badge>
                          ) : '--'}
                        </td>
                        <td className="py-3 px-2">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <p className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2 max-w-[250px] cursor-help">
                                  {stock.rationale || 'No rationale available'}
                                </p>
                              </TooltipTrigger>
                              <TooltipContent side="left" className="max-w-sm">
                                <div className="space-y-1.5">
                                  <p className="text-xs">{stock.rationale}</p>
                                  {stock.key_strength && <p className="text-xs text-emerald-400">Strength: {stock.key_strength}</p>}
                                  {stock.key_risk && <p className="text-xs text-red-400">Risk: {stock.key_risk}</p>}
                                </div>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && !loading && (
        <Card className="bg-[hsl(var(--card))] border border-red-500/30">
          <CardContent className="p-8 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-red-500/10 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-red-400" />
            </div>
            <h3 className="font-display text-lg font-semibold mb-1 text-red-400" data-testid="scan-error-title">Scan Error</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">{error}</p>
            <button onClick={runGodScan} className="px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90" data-testid="retry-scan-btn">
              Retry Scan
            </button>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && !pipeline && !error && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-12 text-center">
            <Sparkles className="w-16 h-16 text-[hsl(var(--muted-foreground))] mx-auto mb-4 opacity-20" />
            <h3 className="font-display text-xl font-semibold mb-2">Ready to Scan</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">Click Launch God Scan to analyze the full NSE + BSE universe</p>
          </CardContent>
        </Card>
      )}

      {/* Scanner History */}
      <ScannerHistory />

      {/* Disclaimer */}
      <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
        <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
          <strong>Disclaimer:</strong> God Mode Scanner uses 3 independent AI models (GPT-4.1, Claude Sonnet, Gemini Flash) to create consensus-driven analysis.
          Scans 3400+ NSE + BSE Group A stocks through a quantitative pre-filter before AI analysis.
          This is NOT investment advice. Past performance does not guarantee future results.
          Always conduct your own research and consult a SEBI-registered financial advisor.
        </p>
      </div>
    </div>
  );
}

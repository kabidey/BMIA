import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { TerminalPanel } from '../components/layout/TerminalPanel';
import {
  TrendingUp, TrendingDown, Minus, Activity, BarChart3, Zap,
  RefreshCw, Timer, ArrowUpRight, ArrowDownRight, Eye,
  Gauge, PieChart as PieChartIcon, Layers, FileText, Bell, Scale, Loader2,
  AlertTriangle, Users, CalendarDays, Newspaper, Sparkles, ChevronRight
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
  Treemap, Cell, ScatterChart, Scatter, ZAxis,
  ReferenceLine, LineChart, Line, PieChart, Pie,
  Tooltip as RTooltip, Legend
} from 'recharts';
import { useApi } from '../hooks/useApi';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// ── Market session from backend (holiday-aware, DB-driven) ──
function MarketStatusBadge() {
  const [session, setSession] = useState(null);
  const [seeding, setSeeding] = useState(false);

  const fetchSession = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/market/session`);
      const d = await res.json();
      setSession(d);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchSession(); }, [fetchSession]);
  useEffect(() => {
    const iv = setInterval(fetchSession, 60000);
    return () => clearInterval(iv);
  }, [fetchSession]);

  const seedHolidays = async () => {
    setSeeding(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/market/holidays/seed`, { method: 'POST' });
      const d = await res.json();
      alert(`Seeded ${d.inserted} new holidays (${d.total} total across 2025-2027)`);
      fetchSession();
    } catch { alert('Failed to seed holidays'); }
    setSeeding(false);
  };

  if (!session) return null;

  const isOpen = session.status === 'open';
  const isPre = session.status === 'preopen' || session.status === 'premarket';
  const dotColor = isOpen ? 'bg-emerald-400' : isPre ? 'bg-amber-400' : 'bg-red-400';
  const textColor = isOpen ? 'text-emerald-400' : isPre ? 'text-amber-400' : 'text-red-400';
  const bgColor = isOpen ? 'bg-emerald-500/10 border-emerald-500/20' : isPre ? 'bg-amber-500/10 border-amber-500/20' : 'bg-red-500/10 border-red-500/20';

  return (
    <div className="flex items-center gap-2">
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${bgColor}`} data-testid="market-status-badge">
        <div className={`w-2 h-2 rounded-full ${dotColor} ${isOpen ? 'animate-pulse' : ''}`} />
        <span className={textColor}>{session.label}</span>
        <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">{session.sublabel}</span>
      </div>
      <button onClick={seedHolidays} disabled={seeding} title="Seed NSE holidays 2025-2027"
        className="w-7 h-7 rounded-lg flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] disabled:opacity-50"
        data-testid="seed-holidays-btn">
        {seeding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Bell className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
}

// ── Flash on change utility ──
function useFlash(value) {
  const prev = useRef(value);
  const [flash, setFlash] = useState(null);
  useEffect(() => {
    if (prev.current !== value && value != null && prev.current != null) {
      setFlash(value > prev.current ? 'up' : value < prev.current ? 'down' : null);
      const t = setTimeout(() => setFlash(null), 450);
      prev.current = value;
      return () => clearTimeout(t);
    }
    prev.current = value;
  }, [value]);
  return flash;
}

// ── Streaming number component ──
function StreamingValue({ value, prefix = '', suffix = '', decimals = 2, className = '' }) {
  const flash = useFlash(value);
  const flashClass = flash === 'up' ? 'bg-[hsla(142,70%,45%,0.12)]' : flash === 'down' ? 'bg-[hsla(0,72%,52%,0.12)]' : '';
  return (
    <span className={`font-mono tabular-nums rounded px-0.5 ${flashClass} ${className}`}
      style={{ transition: 'background-color 0.45s ease' }}>
      {prefix}{value != null ? Number(value).toLocaleString('en-IN', { maximumFractionDigits: decimals, minimumFractionDigits: decimals }) : '--'}{suffix}
    </span>
  );
}

// ── Delta badge ──
function DeltaBadge({ value, suffix = '%' }) {
  if (value == null) return <span className="text-[hsl(var(--muted-foreground))]">--</span>;
  const isUp = value > 0;
  const isZero = value === 0;
  return (
    <span className={`inline-flex items-center gap-0.5 font-mono tabular-nums text-xs ${
      isZero ? 'text-[hsl(var(--muted-foreground))]' : isUp ? 'text-[hsl(var(--up))]' : 'text-[hsl(var(--down))]'
    }`}>
      {!isZero && (isUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />)}
      {isUp ? '+' : ''}{value?.toFixed(2)}{suffix}
    </span>
  );
}

// ── Sector Treemap color ──
function getSectorColor(changePct) {
  if (changePct > 2) return '#16a34a';
  if (changePct > 1) return '#22c55e';
  if (changePct > 0.3) return '#4ade80';
  if (changePct > -0.3) return '#475569';
  if (changePct > -1) return '#f87171';
  if (changePct > -2) return '#ef4444';
  return '#dc2626';
}

// ── VIX Gauge ──
function VIXGauge({ vix }) {
  if (!vix || vix.current == null) return <Skeleton className="h-32" />;
  const val = vix.current;
  const angle = Math.min(Math.max((val / 40) * 180, 0), 180);
  const regimeColors = { calm: 'hsl(var(--up))', watch: 'hsl(var(--amber))', risk: 'hsl(var(--down))', extreme: 'hsl(var(--down))' };
  const needleColor = regimeColors[vix.regime] || 'hsl(var(--muted-foreground))';

  return (
    <div className="flex flex-col items-center" data-testid="vix-gauge">
      <svg viewBox="0 0 200 120" className="w-full max-w-[180px]">
        {/* Gauge arcs */}
        <path d="M 20 100 A 80 80 0 0 1 100 20" fill="none" stroke="hsl(var(--up))" strokeWidth="12" strokeLinecap="round" opacity="0.3" />
        <path d="M 100 20 A 80 80 0 0 1 140 30" fill="none" stroke="hsl(var(--amber))" strokeWidth="12" strokeLinecap="round" opacity="0.3" />
        <path d="M 140 30 A 80 80 0 0 1 180 100" fill="none" stroke="hsl(var(--down))" strokeWidth="12" strokeLinecap="round" opacity="0.3" />
        {/* Needle */}
        <line
          x1="100" y1="100"
          x2={100 + 65 * Math.cos((Math.PI * (180 - angle)) / 180)}
          y2={100 - 65 * Math.sin((Math.PI * (180 - angle)) / 180)}
          stroke={needleColor} strokeWidth="2.5" strokeLinecap="round"
        />
        <circle cx="100" cy="100" r="4" fill={needleColor} />
        {/* Labels */}
        <text x="20" y="115" fontSize="9" fill="hsl(var(--up))" fontFamily="Inter">0</text>
        <text x="90" y="16" fontSize="9" fill="hsl(var(--amber))" fontFamily="Inter">20</text>
        <text x="175" y="115" fontSize="9" fill="hsl(var(--down))" fontFamily="Inter">40</text>
      </svg>
      <div className="text-center -mt-2">
        <p className="font-mono text-2xl font-bold tabular-nums" style={{ color: needleColor }}>{val.toFixed(2)}</p>
        <Badge variant={vix.regime === 'calm' ? 'default' : vix.regime === 'watch' ? 'secondary' : 'destructive'} className="mt-1 text-[10px]">
          {vix.regime_label}
        </Badge>
        <DeltaBadge value={vix.change_pct} />
      </div>
    </div>
  );
}

// ── Custom Treemap Content ──
function CustomTreemapContent({ x, y, width, height, name, change_pct }) {
  if (width < 40 || height < 30) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={getSectorColor(change_pct)} rx={4}
        stroke="hsl(var(--background))" strokeWidth={2} style={{ transition: 'fill 0.3s ease' }} />
      {width > 60 && (
        <>
          <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle" fill="#fff" fontSize={width > 90 ? 11 : 9} fontFamily="Inter" fontWeight="500">
            {name}
          </text>
          <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle" fill="#fff" fontSize={10} fontFamily="monospace" opacity={0.9}>
            {change_pct > 0 ? '+' : ''}{change_pct?.toFixed(2)}%
          </text>
        </>
      )}
    </g>
  );
}

// ── Guidance Intelligence Briefing Card ──
function GuidanceBriefingCard() {
  const [briefing, setBriefing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  const fetchBriefing = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/briefing`);
      if (res.ok) setBriefing(await res.json());
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchBriefing(); }, [fetchBriefing]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/guidance/briefing/refresh`, { method: 'POST' });
      if (res.ok) setBriefing(await res.json());
    } catch { /* */ }
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-[hsl(var(--primary))]/20 bg-gradient-to-r from-[hsl(var(--primary))]/5 to-transparent p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[hsl(var(--primary))] animate-pulse" />
          <Skeleton className="h-5 w-48" />
        </div>
        <Skeleton className="h-4 w-full mt-3" />
        <Skeleton className="h-4 w-3/4 mt-1" />
      </div>
    );
  }

  if (!briefing) return null;

  const critical = briefing.critical_filings || [];
  const insider = briefing.insider_activity || [];
  const agms = briefing.upcoming_agms || [];
  const boardMeetings = briefing.board_meetings || [];
  const topActive = briefing.top_active_stocks || [];

  const totalAlerts = critical.length + insider.length;

  return (
    <div className="rounded-xl border border-[hsl(var(--primary))]/20 bg-gradient-to-br from-[hsl(var(--primary))]/[0.04] via-transparent to-[hsl(var(--amber))]/[0.02] overflow-hidden"
      data-testid="guidance-briefing-card">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[hsl(var(--border))]/50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[hsl(var(--primary))]/15 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-[hsl(var(--primary))]" />
          </div>
          <div>
            <h3 className="text-sm font-display font-semibold tracking-wide" data-testid="briefing-title">
              Guidance Intelligence Briefing
            </h3>
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
              {briefing.generated_at ? new Date(briefing.generated_at).toLocaleString('en-IN', {
                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
              }) : 'Today'}
            </span>
          </div>
          {totalAlerts > 0 && (
            <Badge variant="destructive" className="text-[10px] ml-1 px-1.5 py-0" data-testid="briefing-alert-count">
              {totalAlerts} alert{totalAlerts > 1 ? 's' : ''}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={handleRefresh} disabled={refreshing}
            title="Refresh briefing" data-testid="briefing-refresh-btn">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1" onClick={() => setExpanded(!expanded)}
            data-testid="briefing-expand-btn">
            {expanded ? 'Less' : 'Details'}
            <ChevronRight className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Narrative */}
      {briefing.narrative && (
        <div className="px-4 py-3 text-xs leading-relaxed text-[hsl(var(--foreground))]/85" data-testid="briefing-narrative">
          {briefing.narrative}
        </div>
      )}

      {/* Quick Stats Row */}
      <div className="flex items-center gap-3 px-4 pb-3 flex-wrap">
        {critical.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px]" data-testid="briefing-critical-count">
            <AlertTriangle className="w-3 h-3 text-[hsl(var(--down))]" />
            <span className="text-[hsl(var(--down))] font-medium">{critical.length} Critical</span>
          </div>
        )}
        {insider.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px]" data-testid="briefing-insider-count">
            <Users className="w-3 h-3 text-[hsl(var(--amber))]" />
            <span className="text-[hsl(var(--amber))] font-medium">{insider.length} Insider</span>
          </div>
        )}
        {agms.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px]" data-testid="briefing-agm-count">
            <CalendarDays className="w-3 h-3 text-[hsl(var(--info))]" />
            <span className="text-[hsl(var(--info))] font-medium">{agms.length} AGM/EGM</span>
          </div>
        )}
        {boardMeetings.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px]" data-testid="briefing-board-count">
            <Newspaper className="w-3 h-3 text-[hsl(var(--muted-foreground))]" />
            <span className="text-[hsl(var(--muted-foreground))] font-medium">{boardMeetings.length} Board</span>
          </div>
        )}
        {topActive.length > 0 && (
          <div className="flex items-center gap-1 ml-auto">
            <span className="text-[10px] text-[hsl(var(--muted-foreground))]">Most active:</span>
            {topActive.slice(0, 3).map((s) => (
              <Badge key={s.symbol} variant="outline" className="text-[9px] px-1 py-0 font-mono">
                {s.symbol}
                <span className="text-[hsl(var(--muted-foreground))] ml-0.5">{s.filings_7d}</span>
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-[hsl(var(--border))]/50 px-4 py-3 space-y-3" data-testid="briefing-details">
          {/* Critical Filings */}
          {critical.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <AlertTriangle className="w-3 h-3 text-[hsl(var(--down))]" />
                <span className="text-[11px] font-semibold text-[hsl(var(--down))] uppercase tracking-wider">Critical Filings</span>
              </div>
              <div className="space-y-1">
                {critical.map((f, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs py-1 px-2 rounded-md hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                    onClick={() => navigate(`/analyze/${encodeURIComponent((f.stock_symbol || '') + '.NS')}`)}>
                    <span className="font-mono font-semibold text-[hsl(var(--primary))] shrink-0 w-16">{f.stock_symbol}</span>
                    <span className="text-[hsl(var(--foreground))]/80 truncate flex-1">{f.headline}</span>
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono shrink-0">{(f.news_date || '').slice(0, 10)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Insider Activity */}
          {insider.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Users className="w-3 h-3 text-[hsl(var(--amber))]" />
                <span className="text-[11px] font-semibold text-[hsl(var(--amber))] uppercase tracking-wider">Insider Activity (14d)</span>
              </div>
              <div className="space-y-1">
                {insider.slice(0, 5).map((f, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs py-1 px-2 rounded-md hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                    onClick={() => navigate(`/analyze/${encodeURIComponent((f.stock_symbol || '') + '.NS')}`)}>
                    <span className="font-mono font-semibold text-[hsl(var(--primary))] shrink-0 w-16">{f.stock_symbol}</span>
                    <span className="text-[hsl(var(--foreground))]/80 truncate flex-1">{f.headline}</span>
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono shrink-0">{(f.news_date || '').slice(0, 10)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upcoming AGMs */}
          {agms.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <CalendarDays className="w-3 h-3 text-[hsl(var(--info))]" />
                <span className="text-[11px] font-semibold text-[hsl(var(--info))] uppercase tracking-wider">Upcoming AGMs/EGMs</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {agms.slice(0, 6).map((f, i) => (
                  <Badge key={i} variant="outline" className="text-[10px] px-2 py-0.5 font-mono gap-1 cursor-pointer hover:bg-[hsl(var(--surface-2))]"
                    onClick={() => navigate(`/analyze/${encodeURIComponent((f.stock_symbol || '') + '.NS')}`)}>
                    {f.stock_symbol}
                    <span className="text-[hsl(var(--muted-foreground))]">{(f.news_date || '').slice(5, 10)}</span>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Board Meetings */}
          {boardMeetings.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Newspaper className="w-3 h-3 text-[hsl(var(--muted-foreground))]" />
                <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">Recent Board Meetings</span>
              </div>
              <div className="space-y-1">
                {boardMeetings.map((f, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs py-1 px-2 rounded-md hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                    onClick={() => navigate(`/analyze/${encodeURIComponent((f.stock_symbol || '') + '.NS')}`)}>
                    <span className="font-mono font-semibold text-[hsl(var(--primary))] shrink-0 w-16">{f.stock_symbol}</span>
                    <span className="text-[hsl(var(--foreground))]/80 truncate flex-1">{f.headline}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Go to Guidance */}
          <div className="pt-1">
            <Button variant="outline" size="sm" className="text-xs h-7 gap-1" onClick={() => navigate('/guidance')}
              data-testid="briefing-go-to-guidance">
              <FileText className="w-3 h-3" /> Open Full Guidance
              <ChevronRight className="w-3 h-3" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════════
function DaemonIndicator() {
  const [status, setStatus] = useState(null);
  const [toggling, setToggling] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/daemon/status`);
      setStatus(await res.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);
  useEffect(() => {
    const iv = setInterval(fetchStatus, 30000);
    return () => clearInterval(iv);
  }, [fetchStatus]);

  const handleToggle = async () => {
    setToggling(true);
    try {
      await fetch(`${BACKEND_URL}/api/daemon/toggle`, { method: 'POST' });
      await fetchStatus();
    } catch { /* */ }
    setToggling(false);
  };

  if (!status) return null;

  const isRunning = status.status === 'running' && !status.paused;
  const isPaused = status.paused;

  return (
    <div className="flex items-center gap-1.5" data-testid="daemon-indicator">
      <button onClick={handleToggle} disabled={toggling} title={isPaused ? 'Resume daemon' : 'Pause daemon'}
        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-mono ${
          isRunning ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
          'bg-red-500/10 border-red-500/20 text-red-400'
        } hover:opacity-80 disabled:opacity-50`}>
        <div className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
        {isRunning ? 'Daemon' : 'Paused'}
      </button>
    </div>
  );
}

export default function MarketOverview() {
  const [cockpitData, setCockpitData] = useState(null);
  const [slowData, setSlowData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState('60');
  const [lastRefresh, setLastRefresh] = useState(null);
  const navigate = useNavigate();

  const fetchCockpit = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/market/cockpit`);
      const data = await res.json();
      setCockpitData(data);
      setLastRefresh(new Date());
      setLoading(false);
    } catch (e) {
      console.error('Cockpit fetch error:', e);
      setLoading(false);
    }
  }, []);

  const fetchSlow = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/market/cockpit/slow`);
      const data = await res.json();
      setSlowData(data);
    } catch (e) {
      console.error('Slow modules error:', e);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchCockpit();
    fetchSlow();
  }, [fetchCockpit, fetchSlow]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchCockpit();
    }, parseInt(refreshInterval) * 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchCockpit]);

  const indices = cockpitData?.indices?.indices || [];
  const breadth = cockpitData?.breadth || {};
  const vix = cockpitData?.vix || {};
  const flows = cockpitData?.flows?.flows || [];
  const sectors = cockpitData?.sectors?.sectors || [];
  const clusters = cockpitData?.clusters_52w || {};
  const pcr = cockpitData?.pcr || {};
  const deals = cockpitData?.block_deals?.deals || [];
  const actions = cockpitData?.corporate_actions?.actions || [];
  const shockers = slowData?.volume_shockers?.shockers || [];
  const oiQuad = slowData?.oi_quadrant?.quadrants || {};

  // Primary 5 indices for matrix
  const primaryIndices = indices.filter(i => ['Nifty 50', 'Sensex', 'Bank Nifty', 'Midcap 100', 'Smallcap 100'].includes(i.name));
  const sectoralIndices = indices.filter(i => !['Nifty 50', 'Sensex', 'Bank Nifty', 'Midcap 100', 'Smallcap 100', 'Nifty Next 50'].includes(i.name));

  // OI Quadrant scatter data
  const oiScatterData = [
    ...(oiQuad.long_buildup || []).map(d => ({ ...d, quadrant: 'Long Buildup', fill: 'hsl(var(--up))' })),
    ...(oiQuad.short_covering || []).map(d => ({ ...d, quadrant: 'Short Covering', fill: 'hsl(var(--info))' })),
    ...(oiQuad.short_buildup || []).map(d => ({ ...d, quadrant: 'Short Buildup', fill: 'hsl(var(--down))' })),
    ...(oiQuad.long_unwinding || []).map(d => ({ ...d, quadrant: 'Long Unwinding', fill: 'hsl(var(--amber))' })),
  ];

  if (loading && !cockpitData) {
    return (
      <div className="p-4 lg:p-6 max-w-[1920px] mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary))]/20 flex items-center justify-center">
            <Activity className="w-6 h-6 text-[hsl(var(--primary))] animate-pulse" />
          </div>
          <div>
            <Skeleton className="h-7 w-72" />
            <Skeleton className="h-4 w-48 mt-1" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <Skeleton className="lg:col-span-8 h-64" />
          <Skeleton className="lg:col-span-4 h-64" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <Skeleton className="lg:col-span-7 h-80" />
          <Skeleton className="lg:col-span-5 h-80" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-6 max-w-[1920px] mx-auto space-y-4 lg:space-y-5" data-testid="market-cockpit">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary))]/20 flex items-center justify-center">
            <Activity className="w-6 h-6 text-[hsl(var(--primary))]" />
          </div>
          <div>
            <h1 className="font-display text-2xl lg:text-3xl font-bold tracking-tight" data-testid="cockpit-title">
              Market Intelligence Cockpit
            </h1>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Liquidity Flow &bull; Sentiment &bull; Sector Rotation &bull; Derivatives
            </p>
          </div>
          <MarketStatusBadge />
          <DaemonIndicator />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
            <Timer className="w-3.5 h-3.5" />
            <Select value={refreshInterval} onValueChange={setRefreshInterval} data-testid="refresh-interval-select">
              <SelectTrigger className="w-20 h-7 text-xs bg-[hsl(var(--surface-2))]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30s</SelectItem>
                <SelectItem value="60">60s</SelectItem>
                <SelectItem value="120">2m</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center gap-1.5">
              <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} className="scale-75" data-testid="auto-refresh-toggle" />
              <span>Auto</span>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => { fetchCockpit(); fetchSlow(); }} data-testid="manual-refresh-btn">
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
          </Button>
          {lastRefresh && (
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
              {lastRefresh.toLocaleTimeString('en-IN')}
            </span>
          )}
        </div>
      </div>

      {/* ── Guidance Briefing Card ── */}
      <GuidanceBriefingCard />

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 1: MACRO VIEW (Market Weather)                              */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4">
        {/* Indices Matrix (8 cols) */}
        <TerminalPanel title="Major Indices" subtitle={`${primaryIndices.length} tracked`}
          className="lg:col-span-8" updatedAt={cockpitData?.indices?.updated_at} data-testid="macro-indices-matrix">
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="indices-table">
              <thead>
                <tr className="text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
                  <th className="py-2 px-2 text-left font-medium">Index</th>
                  <th className="py-2 px-2 text-right font-medium">LTP</th>
                  <th className="py-2 px-2 text-right font-medium">Chg</th>
                  <th className="py-2 px-2 text-right font-medium">%Chg</th>
                  <th className="py-2 px-2 text-center font-medium">Day Range</th>
                  <th className="py-2 px-2 text-center font-medium">Breadth</th>
                </tr>
              </thead>
              <tbody>
                {primaryIndices.map((idx) => {
                  const rangePct = idx.high && idx.low && idx.high !== idx.low
                    ? ((idx.last - idx.low) / (idx.high - idx.low)) * 100
                    : 50;
                  return (
                    <tr key={idx.symbol} className="border-b border-[hsl(var(--border))]/30 hover:bg-[hsl(var(--surface-2))]" style={{ height: '48px' }}
                      data-testid={`indices-row-${idx.name.toLowerCase().replace(/\s+/g, '-')}`}>
                      <td className="py-2 px-2">
                        <span className="font-medium text-sm">{idx.name}</span>
                      </td>
                      <td className="py-2 px-2 text-right">
                        <StreamingValue value={idx.last} decimals={2} className="text-sm font-bold" />
                      </td>
                      <td className="py-2 px-2 text-right">
                        <DeltaBadge value={idx.change} suffix="" />
                      </td>
                      <td className="py-2 px-2 text-right">
                        <DeltaBadge value={idx.change_pct} />
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">{idx.low?.toLocaleString('en-IN')}</span>
                          <div className="flex-1 h-1.5 bg-[hsl(var(--surface-3))] rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${idx.change_pct >= 0 ? 'bg-[hsl(var(--up))]' : 'bg-[hsl(var(--down))]'}`}
                              style={{ width: `${Math.max(5, Math.min(95, rangePct))}%`, transition: 'width 0.3s ease' }} />
                          </div>
                          <span className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">{idx.high?.toLocaleString('en-IN')}</span>
                        </div>
                      </td>
                      <td className="py-2 px-2 text-center">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <span className="text-[10px] font-mono">
                                <span className="text-[hsl(var(--up))]">{idx.advances}</span>
                                <span className="text-[hsl(var(--muted-foreground))]"> / </span>
                                <span className="text-[hsl(var(--down))]">{idx.declines}</span>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent><p>Advances: {idx.advances} | Declines: {idx.declines} | Unchanged: {idx.unchanged}</p></TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {/* Sectoral indices mini row */}
          {sectoralIndices.length > 0 && (
            <div className="mt-3 pt-2 border-t border-[hsl(var(--border))]/50">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-widest mb-2">Sectoral Indices</p>
              <div className="flex flex-wrap gap-2">
                {sectoralIndices.map((idx) => (
                  <Badge key={idx.symbol} variant="outline"
                    className={`text-[10px] font-mono gap-1 ${idx.change_pct >= 0 ? 'border-[hsl(var(--up))]/30 text-[hsl(var(--up))]' : 'border-[hsl(var(--down))]/30 text-[hsl(var(--down))]'}`}>
                    {idx.name} <DeltaBadge value={idx.change_pct} />
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </TerminalPanel>

        {/* Right Rail: VIX + Breadth + Flows (4 cols) */}
        <div className="lg:col-span-4 space-y-3 lg:space-y-4">
          {/* VIX Gauge */}
          <TerminalPanel title="India VIX" subtitle="Regime" updatedAt={vix.updated_at}>
            <VIXGauge vix={vix} />
          </TerminalPanel>

          {/* Advance/Decline */}
          <TerminalPanel title="Market Breadth" subtitle="Nifty 500" updatedAt={breadth.updated_at} data-testid="breadth-panel">
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-[hsl(var(--up))] font-medium">Advancing: {breadth.advances || 0}</span>
                <span className="font-mono font-bold">A/D: {breadth.ad_ratio || '--'}</span>
                <span className="text-[hsl(var(--down))] font-medium">Declining: {breadth.declines || 0}</span>
              </div>
              <div className="h-3 bg-[hsl(var(--surface-3))] rounded-full overflow-hidden flex">
                <div className="bg-[hsl(var(--up))] rounded-l-full" style={{ width: `${breadth.advance_pct || 50}%`, transition: 'width 0.3s ease' }} />
                <div className="bg-[hsl(var(--surface-4))]" style={{ width: `${100 - (breadth.advance_pct || 50) - (breadth.decline_pct || 50)}%` }} />
                <div className="bg-[hsl(var(--down))] rounded-r-full" style={{ width: `${breadth.decline_pct || 50}%`, transition: 'width 0.3s ease' }} />
              </div>
              <div className="flex justify-between text-[10px] text-[hsl(var(--muted-foreground))]">
                <span>{breadth.advance_pct || '--'}%</span>
                <span>Unch: {breadth.unchanged || 0}</span>
                <span>{breadth.decline_pct || '--'}%</span>
              </div>
            </div>
          </TerminalPanel>

          {/* FII/DII Flows Mini Chart */}
          <TerminalPanel title="FII Derivatives Flow" subtitle={"Net \u20B9 Cr"} updatedAt={cockpitData?.flows?.updated_at} data-testid="flows-fii-dii-chart">
            {flows.length > 0 ? (
              <ResponsiveContainer width="100%" height={100}>
                <BarChart data={flows} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="display_date" tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} />
                  <RTooltip contentStyle={{ background: 'hsl(222, 18%, 8%)', border: '1px solid hsl(222, 14%, 18%)', borderRadius: 8, fontSize: 11 }} />
                  <Bar dataKey="fii_net" name="FII Net">
                    {flows.map((entry, i) => (
                      <Cell key={i} fill={entry.fii_net >= 0 ? 'hsl(var(--up))' : 'hsl(var(--down))'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <Skeleton className="h-24" />}
          </TerminalPanel>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 2: MICRO VIEW (Where the Action Is)                        */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4">
        {/* Sector Treemap (7 cols) */}
        <TerminalPanel title="Sector Rotation" subtitle={`${sectors.length} sectors`}
          className="lg:col-span-7" updatedAt={cockpitData?.sectors?.updated_at} data-testid="sector-treemap">
          {sectors.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <Treemap
                data={sectors.map(s => ({ name: s.name, size: s.weight, change_pct: s.change_pct }))}
                dataKey="size"
                aspectRatio={4 / 3}
                content={<CustomTreemapContent />}
              />
            </ResponsiveContainer>
          ) : <Skeleton className="h-64" />}
          {/* Legend */}
          <div className="flex items-center justify-center gap-2 mt-2">
            {[{ label: '<-2%', color: '#dc2626' }, { label: '-1%', color: '#ef4444' }, { label: '0', color: '#475569' }, { label: '+1%', color: '#22c55e' }, { label: '>+2%', color: '#16a34a' }].map(l => (
              <div key={l.label} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: l.color }} />
                <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">{l.label}</span>
              </div>
            ))}
          </div>
        </TerminalPanel>

        {/* Volume Shockers + 52W Clusters (5 cols) */}
        <div className="lg:col-span-5 space-y-3 lg:space-y-4">
          {/* Volume Shockers */}
          <TerminalPanel title="Volume Shockers" subtitle={"\u22653x Avg"} updatedAt={slowData?.volume_shockers?.updated_at}
            loading={!slowData} data-testid="volume-shockers-table">
            <ScrollArea className="h-[160px]">
              {shockers.length > 0 ? (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
                      <th className="py-1 px-1 text-left">Symbol</th>
                      <th className="py-1 px-1 text-right">Vol xAvg</th>
                      <th className="py-1 px-1 text-right">%Chg</th>
                      <th className="py-1 px-1 text-center">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shockers.slice(0, 10).map((s) => (
                      <tr key={s.symbol} className="border-b border-[hsl(var(--border))]/20 hover:bg-[hsl(var(--surface-2))] cursor-pointer"
                        onClick={() => navigate(`/analyze/${encodeURIComponent(s.symbol)}`)}>
                        <td className="py-1.5 px-1 font-mono font-medium">{s.display_name}</td>
                        <td className="py-1.5 px-1 text-right">
                          <Badge variant={s.vol_ratio >= 5 ? 'default' : 'secondary'} className="text-[10px] px-1 py-0">
                            {s.vol_ratio}x
                          </Badge>
                        </td>
                        <td className="py-1.5 px-1 text-right"><DeltaBadge value={s.change_pct} /></td>
                        <td className="py-1.5 px-1 text-center">
                          <Badge variant={s.is_breakout ? 'default' : 'outline'} className="text-[10px] px-1 py-0">
                            {s.is_breakout ? 'Breakout' : 'Spike'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-[hsl(var(--muted-foreground))]">
                  {slowData ? 'No volume shockers found' : 'Scanning...'}
                </div>
              )}
            </ScrollArea>
          </TerminalPanel>

          {/* 52W Clusters */}
          <TerminalPanel title="52-Week Extremes" subtitle={`${clusters.high_count || 0}H / ${clusters.low_count || 0}L`}
            updatedAt={clusters.updated_at}>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center p-3 bg-[hsl(var(--up))]/10 rounded-lg border border-[hsl(var(--up))]/20">
                <TrendingUp className="w-5 h-5 text-[hsl(var(--up))] mx-auto" />
                <p className="font-mono text-2xl font-bold text-[hsl(var(--up))] mt-1" data-testid="52w-high-count">{clusters.high_count || 0}</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))]">New 52W Highs</p>
              </div>
              <div className="text-center p-3 bg-[hsl(var(--down))]/10 rounded-lg border border-[hsl(var(--down))]/20">
                <TrendingDown className="w-5 h-5 text-[hsl(var(--down))] mx-auto" />
                <p className="font-mono text-2xl font-bold text-[hsl(var(--down))] mt-1" data-testid="52w-low-count">{clusters.low_count || 0}</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))]">New 52W Lows</p>
              </div>
            </div>
          </TerminalPanel>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 3: DERIVATIVES & SENTIMENT                                  */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4">
        {/* PCR Gauges (4 cols) */}
        <TerminalPanel title="Put-Call Ratio" subtitle="OI Based" className="lg:col-span-4" updatedAt={pcr.updated_at}>
          <div className="grid grid-cols-2 gap-4">
            {[{ key: 'nifty', label: 'Nifty' }, { key: 'banknifty', label: 'Bank Nifty' }].map(({ key, label }) => {
              const d = pcr[key];
              if (!d || !d.pcr) return (
                <div key={key} className="text-center p-3 bg-[hsl(var(--surface-2))] rounded-lg">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
                  <Skeleton className="h-8 w-16 mx-auto mt-2" />
                </div>
              );
              const pcrColor = d.sentiment === 'put_heavy' || d.sentiment === 'mildly_bullish'
                ? 'hsl(var(--up))'
                : d.sentiment === 'call_heavy' ? 'hsl(var(--down))' : 'hsl(var(--amber))';
              return (
                <div key={key} className="text-center p-3 bg-[hsl(var(--surface-2))] rounded-lg" data-testid={`pcr-${key}`}>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
                  <p className="font-mono text-2xl font-bold mt-1" style={{ color: pcrColor }}>{d.pcr}</p>
                  <Badge variant="outline" className="mt-1 text-[10px]" style={{ borderColor: pcrColor, color: pcrColor }}>
                    {d.label}
                  </Badge>
                  {d.expiry && <p className="text-[9px] text-[hsl(var(--muted-foreground))] mt-1">Exp: {d.expiry}</p>}
                </div>
              );
            })}
          </div>
        </TerminalPanel>

        {/* OI Quadrant (8 cols) */}
        <TerminalPanel title="OI Buildup Quadrant" subtitle={"Price\u0394 vs Volume\u0394"}
          className="lg:col-span-8" updatedAt={slowData?.oi_quadrant?.updated_at}
          loading={!slowData} data-testid="oi-quadrant-chart">
          {oiScatterData.length > 0 ? (
            <div className="flex gap-4">
              <div className="flex-1">
                <ResponsiveContainer width="100%" height={220}>
                  <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" dataKey="price_change" name="Price %" unit="%"
                      tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
                      label={{ value: 'Price Change %', position: 'bottom', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis type="number" dataKey="volume_change" name="Vol %" unit="%"
                      tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} />
                    <ReferenceLine x={0} stroke="hsl(var(--border))" strokeWidth={1.5} />
                    <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1.5} />
                    <RTooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      contentStyle={{ background: 'hsl(222, 18%, 8%)', border: '1px solid hsl(222, 14%, 18%)', borderRadius: 8, fontSize: 11 }}
                      formatter={(val, name) => [val?.toFixed(2) + '%', name]}
                      labelFormatter={(val) => ''}
                    />
                    <Scatter data={oiScatterData} name="Stocks">
                      {oiScatterData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              {/* Quadrant legend + counts */}
              <div className="w-40 space-y-2 text-xs">
                {[
                  { label: 'Long Buildup', key: 'long_buildup', color: 'hsl(var(--up))', desc: 'Price\u2191 Vol\u2191' },
                  { label: 'Short Covering', key: 'short_covering', color: 'hsl(var(--info))', desc: 'Price\u2191 Vol\u2193' },
                  { label: 'Short Buildup', key: 'short_buildup', color: 'hsl(var(--down))', desc: 'Price\u2193 Vol\u2191' },
                  { label: 'Long Unwinding', key: 'long_unwinding', color: 'hsl(var(--amber))', desc: 'Price\u2193 Vol\u2193' },
                ].map(q => (
                  <div key={q.key} className="p-2 bg-[hsl(var(--surface-2))] rounded-lg">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: q.color }} />
                      <span className="font-medium" style={{ color: q.color }}>{q.label}</span>
                    </div>
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{q.desc}</p>
                    <p className="font-mono font-bold mt-0.5">{(oiQuad[q.key] || []).length} stocks</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-xs text-[hsl(var(--muted-foreground))]">
              {slowData ? 'No OI data available' : 'Loading derivatives data...'}
            </div>
          )}
        </TerminalPanel>
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 4: CORPORATE ACTIONS & NEWS                                 */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4">
        {/* Block/Bulk Deals (7 cols) */}
        <TerminalPanel title="Block & Bulk Deals" subtitle={`${deals.length} recent`}
          className="lg:col-span-7" updatedAt={cockpitData?.block_deals?.updated_at} data-testid="block-bulk-feed">
          <ScrollArea className="h-[200px]">
            {deals.length > 0 ? (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))] sticky top-0 bg-[hsl(var(--card))]">
                    <th className="py-1.5 px-1 text-left">Date</th>
                    <th className="py-1.5 px-1 text-left">Symbol</th>
                    <th className="py-1.5 px-1 text-left">Client</th>
                    <th className="py-1.5 px-1 text-center">Side</th>
                    <th className="py-1.5 px-1 text-right">Value (Cr)</th>
                  </tr>
                </thead>
                <tbody>
                  {deals.map((d, i) => (
                    <tr key={i} className="border-b border-[hsl(var(--border))]/20 hover:bg-[hsl(var(--surface-2))]">
                      <td className="py-1.5 px-1 font-mono text-[hsl(var(--muted-foreground))]">{d.date}</td>
                      <td className="py-1.5 px-1">
                        <span className="font-mono font-medium cursor-pointer hover:text-[hsl(var(--primary))]"
                          onClick={() => navigate(`/analyze/${encodeURIComponent(d.symbol + '.NS')}`)}>
                          {d.symbol}
                        </span>
                      </td>
                      <td className="py-1.5 px-1 text-[hsl(var(--muted-foreground))] truncate max-w-[200px]">{d.client}</td>
                      <td className="py-1.5 px-1 text-center">
                        <Badge variant={d.side === 'BUY' ? 'default' : 'destructive'} className="text-[10px] px-1.5 py-0">
                          {d.side}
                        </Badge>
                      </td>
                      <td className="py-1.5 px-1 text-right font-mono tabular-nums">
                        {d.value_cr > 0 ? `\u20B9${d.value_cr.toLocaleString('en-IN')}` : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <Skeleton className="h-40" />}
          </ScrollArea>
        </TerminalPanel>

        {/* Corporate Actions (5 cols) */}
        <TerminalPanel title="Corporate Actions" subtitle="This Week"
          className="lg:col-span-5" updatedAt={cockpitData?.corporate_actions?.updated_at}>
          <ScrollArea className="h-[200px]">
            {actions.length > 0 ? (
              <div className="space-y-1.5">
                {actions.map((a, i) => {
                  const catColors = {
                    dividend: 'hsl(var(--up))', split: 'hsl(var(--info))',
                    bonus: 'hsl(var(--amber))', rights: 'hsl(var(--primary))',
                    meeting: 'hsl(var(--muted-foreground))', other: 'hsl(var(--muted-foreground))'
                  };
                  return (
                    <div key={i} className="flex items-start gap-2 p-2 rounded-lg hover:bg-[hsl(var(--surface-2))] text-xs">
                      <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: catColors[a.category] }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-medium cursor-pointer hover:text-[hsl(var(--primary))]"
                            onClick={() => navigate(`/analyze/${encodeURIComponent(a.symbol + '.NS')}`)}>
                            {a.symbol}
                          </span>
                          <Badge variant="outline" className="text-[9px] px-1 py-0 capitalize" style={{ borderColor: catColors[a.category], color: catColors[a.category] }}>
                            {a.category}
                          </Badge>
                        </div>
                        <p className="text-[hsl(var(--muted-foreground))] truncate mt-0.5">{a.subject}</p>
                        <p className="text-[10px] text-[hsl(var(--muted-foreground))]/60 font-mono mt-0.5">Ex: {a.ex_date}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : <Skeleton className="h-40" />}
          </ScrollArea>
        </TerminalPanel>
      </div>

      {/* Disclaimer */}
      <div className="text-[10px] text-[hsl(var(--muted-foreground))]/50 text-center py-2" data-testid="sebi-disclaimer">
        Data aggregated from licensed market data providers. For educational purposes only. Not investment advice. Consult a SEBI-registered advisor.
      </div>
    </div>
  );
}

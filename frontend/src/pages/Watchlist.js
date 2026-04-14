import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, TrendingUp, TrendingDown, ChevronRight, ArrowRightLeft, Clock, Zap, Target, Shield, Rocket, BarChart3, Gem, Loader2, IndianRupee, ArrowUpRight, ArrowDownRight, History, CheckCircle2, Plus } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STRATEGY_ICONS = {
  bespoke_forward_looking: Rocket,
  quick_entry: Zap,
  long_term: Shield,
  swing: ArrowRightLeft,
  alpha_generator: Target,
  value_stocks: Gem,
};

const STRATEGY_COLORS = {
  bespoke_forward_looking: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30',
  quick_entry: 'from-amber-500/20 to-orange-500/20 border-amber-500/30',
  long_term: 'from-emerald-500/20 to-green-500/20 border-emerald-500/30',
  swing: 'from-purple-500/20 to-violet-500/20 border-purple-500/30',
  alpha_generator: 'from-red-500/20 to-rose-500/20 border-red-500/30',
  value_stocks: 'from-teal-500/20 to-cyan-500/20 border-teal-500/30',
};

const STRATEGY_ACCENT = {
  bespoke_forward_looking: 'text-blue-400',
  quick_entry: 'text-amber-400',
  long_term: 'text-emerald-400',
  swing: 'text-purple-400',
  alpha_generator: 'text-red-400',
  value_stocks: 'text-teal-400',
};

function SignalBadge({ signal }) {
  if (!signal || signal === '?') return null;
  const colors = {
    BULLISH: 'bg-emerald-500/20 text-emerald-400',
    NEUTRAL: 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]',
    BEARISH: 'bg-red-500/20 text-red-400',
  };
  return <span className={`text-[9px] font-mono px-1 py-0.5 rounded ${colors[signal] || colors.NEUTRAL}`}>{signal}</span>;
}

function GradeBadge({ grade }) {
  if (!grade || grade === '?') return null;
  const colors = { A: 'text-emerald-400', B: 'text-blue-400', C: 'text-amber-400', D: 'text-red-400' };
  return <span className={`text-[9px] font-bold ${colors[grade] || 'text-[hsl(var(--muted-foreground))]'}`}>{grade}</span>;
}

function HoldingsTable({ holdings, accent }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
          <th className="px-3 py-2 text-left">Stock</th>
          <th className="px-3 py-2 text-right hidden sm:table-cell">Entry</th>
          <th className="px-3 py-2 text-right">Current</th>
          <th className="px-3 py-2 text-right hidden sm:table-cell">Qty</th>
          <th className="px-3 py-2 text-right">P&L</th>
          <th className="px-3 py-2 text-right hidden md:table-cell">Weight</th>
          <th className="px-3 py-2 text-left hidden lg:table-cell">AI Intelligence</th>
        </tr>
      </thead>
      <tbody>
        {holdings.map((h, i) => (
          <tr key={h.symbol || i} className="border-b border-[hsl(var(--border))]/50 hover:bg-[hsl(var(--surface-2))]" data-testid={`holding-${i}`}>
            <td className="px-3 py-2">
              <div className="flex items-center gap-1.5">
                <span className={`font-mono font-semibold text-xs ${accent}`}>{h.symbol?.replace('.NS', '')}</span>
                {h.consensus_votes > 1 && (
                  <span className="text-[8px] bg-amber-500/20 text-amber-400 px-1 rounded font-mono" title={`Picked by ${h.consensus_votes} LLMs`}>{h.consensus_votes}V</span>
                )}
              </div>
              {h.sector && <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{h.sector}</p>}
              <div className="flex items-center gap-1 mt-0.5">
                <SignalBadge signal={h.technical_signal} />
                <GradeBadge grade={h.fundamental_grade} />
              </div>
            </td>
            <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--foreground))] hidden sm:table-cell">{h.entry_price?.toFixed(2)}</td>
            <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--foreground))]">{h.current_price?.toFixed(2)}</td>
            <td className="px-3 py-2 text-right font-mono text-xs text-[hsl(var(--muted-foreground))] hidden sm:table-cell">{h.quantity}</td>
            <td className="px-3 py-2 text-right">
              <span className={`font-mono text-xs font-semibold ${(h.pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {(h.pnl_pct || 0) >= 0 ? '+' : ''}{(h.pnl_pct || 0).toFixed(2)}%
              </span>
              <p className={`font-mono text-[10px] ${(h.pnl || 0) >= 0 ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
                {(h.pnl || 0) >= 0 ? '+' : ''}{(h.pnl || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
            </td>
            <td className="px-3 py-2 text-right font-mono text-[10px] text-[hsl(var(--muted-foreground))] hidden md:table-cell">{h.weight?.toFixed(1)}%</td>
            <td className="px-3 py-2 text-left hidden lg:table-cell max-w-sm">
              <p className="text-[10px] text-[hsl(var(--foreground))] line-clamp-2">{h.rationale?.slice(0, 140)}</p>
              {h.filing_insight && h.filing_insight !== 'No recent filings' && (
                <p className="text-[9px] text-blue-400/80 mt-0.5 line-clamp-1">BSE: {h.filing_insight}</p>
              )}
              {h.risk_flag && (
                <p className="text-[9px] text-red-400/70 mt-0.5 line-clamp-1">Risk: {h.risk_flag}</p>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SwapCard({ change, index }) {
  const outgoing = change.outgoing || {};
  const incoming = change.incoming || {};

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden" data-testid={`swap-card-${index}`}>
      <div className="grid grid-cols-[1fr_auto_1fr] gap-0">
        {/* Outgoing */}
        <div className="p-3 border-r border-[hsl(var(--border))] bg-red-500/5">
          <div className="flex items-center gap-1.5 mb-2">
            <ArrowDownRight className="w-3.5 h-3.5 text-red-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-red-400">Removed</span>
          </div>
          <p className="font-mono font-bold text-sm text-red-300">{outgoing.symbol?.replace('.NS', '')}</p>
          {outgoing.name && <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{outgoing.name}</p>}
          {outgoing.pnl_pct !== undefined && (
            <p className={`text-xs font-mono mt-1 ${outgoing.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              Exit P&L: {outgoing.pnl_pct >= 0 ? '+' : ''}{outgoing.pnl_pct?.toFixed(2)}%
            </p>
          )}
          {outgoing.entry_price && outgoing.exit_price && (
            <p className="text-[10px] font-mono text-[hsl(var(--muted-foreground))] mt-0.5">
              {outgoing.entry_price?.toFixed(2)} → {outgoing.exit_price?.toFixed(2)}
            </p>
          )}
          {outgoing.rationale && (
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-2 leading-relaxed border-t border-red-500/10 pt-2">{outgoing.rationale}</p>
          )}
        </div>

        {/* Arrow */}
        <div className="flex items-center justify-center px-2 bg-[hsl(var(--surface-2))]">
          <ArrowRightLeft className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
        </div>

        {/* Incoming */}
        <div className="p-3 border-l border-[hsl(var(--border))] bg-emerald-500/5">
          <div className="flex items-center gap-1.5 mb-2">
            <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">Added</span>
          </div>
          <p className="font-mono font-bold text-sm text-emerald-300">{incoming.symbol?.replace('.NS', '')}</p>
          {incoming.name && <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{incoming.name}</p>}
          {incoming.sector && (
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{incoming.sector}</p>
          )}
          <p className="text-xs font-mono text-[hsl(var(--foreground))] mt-1">
            Entry: {incoming.entry_price?.toFixed(2)} | Qty: {incoming.quantity} | W: {incoming.weight?.toFixed(1)}%
          </p>
          {incoming.rationale && (
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-2 leading-relaxed border-t border-emerald-500/10 pt-2">{incoming.rationale}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function PortfolioCard({ portfolio, strategies, rebalanceLogs }) {
  const navigate = useNavigate();
  const type = portfolio.type;
  const cfg = strategies[type] || {};
  const Icon = STRATEGY_ICONS[type] || BarChart3;
  const colors = STRATEGY_COLORS[type] || '';
  const accent = STRATEGY_ACCENT[type] || 'text-[hsl(var(--primary))]';
  const isConstructing = portfolio.status === 'constructing';
  const isError = portfolio.status === 'error';
  const isActive = portfolio.status === 'active';
  const [constructing, setConstructing] = useState(false);

  const handleConstruct = async (e) => {
    e.stopPropagation();
    setConstructing(true);
    fetch(`${BACKEND_URL}/api/portfolios/${type}/construct`, { method: 'POST' }).catch(() => {});
  };

  const pnl = portfolio.total_pnl || 0;
  const pnlPct = portfolio.total_pnl_pct || 0;
  const holdings = portfolio.holdings || [];

  return (
    <div className="space-y-0" data-testid={`portfolio-card-${type}`}>
      <div
        className={`p-4 rounded-xl border cursor-pointer bg-gradient-to-br ${colors} transition-all hover:scale-[1.01]`}
        onClick={() => isActive ? navigate(`/portfolio/${type}`) : null}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={`w-10 h-10 rounded-lg bg-[hsl(var(--surface-1))] flex items-center justify-center flex-shrink-0 ${accent}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[hsl(var(--foreground))]">{cfg.name || portfolio.name}</h3>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{cfg.description?.slice(0, 80) || ''}</p>
              <div className="flex items-center gap-3 mt-1">
                <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{cfg.horizon || portfolio.horizon}</p>
                {portfolio.pipeline && <span className="text-[9px] bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded font-mono">{portfolio.pipeline}</span>}
                {portfolio.last_rebalanced && (
                  <span className="text-[10px] text-amber-400/80 flex items-center gap-0.5">
                    <History className="w-2.5 h-2.5" />
                    Rebalanced {new Date(portfolio.last_rebalanced).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="text-right flex-shrink-0 ml-4">
            {(isConstructing || isError) && (
              <button onClick={handleConstruct} disabled={constructing}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25 disabled:opacity-50"
                data-testid={`construct-btn-${type}`}>
                {constructing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                {constructing ? 'Building... ~2-3 min' : 'Construct Now'}
              </button>
            )}
            {isActive && (
              <>
                <p className="text-lg font-mono font-bold text-[hsl(var(--foreground))]">
                  <IndianRupee className="w-3 h-3 inline" />{(portfolio.current_value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
                <p className={`text-sm font-mono flex items-center justify-end gap-0.5 ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pnl >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {pnl >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                  <span className="ml-1 text-xs">({pnl >= 0 ? '+' : ''}{pnl.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })})</span>
                </p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">
                  {holdings.length} stocks | W:{holdings.filter(h => (h.pnl_pct||0) > 0).length} L:{holdings.filter(h => (h.pnl_pct||0) < 0).length}
                </p>
              </>
            )}
          </div>
        </div>

        {isActive && (
          <div className="flex items-center justify-center mt-2 text-[hsl(var(--muted-foreground))]">
            <span className="text-[10px] mr-1">View Details</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </div>
        )}
      </div>
    </div>
  );
}


function GlobalRebalanceActivity({ logs }) {
  const rebalancedLogs = logs.filter(l => l.action === 'REBALANCE' && l.changes?.length > 0);
  if (rebalancedLogs.length === 0) return null;

  return (
    <div className="space-y-3" data-testid="global-rebalance-activity">
      <div className="flex items-center gap-2">
        <History className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">Recent Rebalancing Activity</h3>
        <span className="text-[10px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full font-mono">{rebalancedLogs.length} swap{rebalancedLogs.length !== 1 ? 's' : ''}</span>
      </div>
      {rebalancedLogs.slice(0, 5).map((log, i) => (
        <div key={i} className="p-3 rounded-lg bg-[hsl(var(--surface-1))] border border-amber-500/20" data-testid={`global-rebalance-${i}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs font-semibold text-amber-400 capitalize">{log.portfolio_type?.replace(/_/g, ' ')}</span>
            </div>
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
              {log.timestamp ? new Date(log.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
            </span>
          </div>
          {log.changes?.map((ch, j) => (
            <SwapCard key={j} change={ch} index={j} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function Watchlist() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [portfolios, setPortfolios] = useState([]);
  const [strategies, setStrategies] = useState({});
  const [rebalanceLogs, setRebalanceLogs] = useState([]);
  const [customPortfolios, setCustomPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [ovRes, pfRes, logRes, cpRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/portfolios/overview`),
        fetch(`${BACKEND_URL}/api/portfolios`),
        fetch(`${BACKEND_URL}/api/portfolios/rebalance-log-all/recent?limit=30`),
        fetch(`${BACKEND_URL}/api/custom-portfolios`),
      ]);
      const ovData = await ovRes.json();
      const pfData = await pfRes.json();
      const logData = await logRes.json();
      const cpData = await cpRes.json();

      setOverview(ovData);
      setPortfolios(pfData.portfolios || []);
      setStrategies(pfData.strategies || {});
      setRebalanceLogs(logData.logs || []);
      setCustomPortfolios(cpData.portfolios || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const allStrategies = Object.keys(STRATEGY_ICONS);
  const portfolioMap = {};
  for (const p of portfolios) {
    portfolioMap[p.type] = p;
  }

  const totalPnl = overview?.total_pnl || 0;
  const totalPnlPct = overview?.total_pnl_pct || 0;

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-[1920px]" data-testid="portfolio-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-display font-bold text-[hsl(var(--foreground))]" data-testid="portfolio-title">
            Autonomous Portfolios
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            6 AI-managed strategies | God Mode 3-LLM consensus | Zero human intervention
          </p>
        </div>
        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50"
          data-testid="refresh-portfolios-btn">
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Global Summary */}
      {overview && (overview.active_portfolios > 0 || overview.pending_construction > 0) && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3" data-testid="global-summary">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-3">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Total Capital</p>
              <p className="text-base font-mono font-bold text-[hsl(var(--foreground))]">{(overview.total_capital / 100000).toFixed(0)}L</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-3">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Current Value</p>
              <p className="text-base font-mono font-bold text-[hsl(var(--foreground))]">{overview.total_value > 0 ? `${(overview.total_value / 100000).toFixed(1)}L` : '--'}</p>
            </CardContent>
          </Card>
          <Card className={`border ${totalPnl >= 0 ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
            <CardContent className="p-3">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Total P&L</p>
              <p className={`text-base font-mono font-bold ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {overview.total_value > 0 ? `${totalPnl >= 0 ? '+' : ''}${(totalPnl / 100000).toFixed(2)}L` : '--'}
              </p>
            </CardContent>
          </Card>
          <Card className={`border ${totalPnlPct >= 0 ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
            <CardContent className="p-3">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Return %</p>
              <p className={`text-base font-mono font-bold ${totalPnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {overview.total_value > 0 ? `${totalPnlPct >= 0 ? '+' : ''}${totalPnlPct.toFixed(2)}%` : '--'}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-3">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Active</p>
              <p className="text-base font-mono font-bold text-emerald-400">{overview.active_portfolios}/6</p>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-3">
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Rebalance Logs</p>
              <p className="text-base font-mono font-bold text-amber-400">{rebalanceLogs.length}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Portfolio Cards */}
      {loading ? (
        <div className="space-y-3" data-testid="loading-portfolios">
          {[...Array(6)].map((_, i) => <div key={i} className="h-28 rounded-xl bg-[hsl(var(--surface-2))] animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="portfolio-grid">
          {allStrategies.map(type => {
            const p = portfolioMap[type];
            if (!p) {
              return <UnconstructedCard key={type} type={type} strategies={strategies} BACKEND_URL={BACKEND_URL} />;
            }
            return (
              <PortfolioCard
                key={type}
                portfolio={p}
                strategies={strategies}
                rebalanceLogs={rebalanceLogs}
              />
            );
          })}
        </div>
      )}

      {/* Global Rebalance Activity */}
      <GlobalRebalanceActivity logs={rebalanceLogs} />

      {/* Custom Portfolios Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-display font-bold text-[hsl(var(--foreground))]">Your Portfolios</h2>
          <button onClick={() => navigate('/portfolio/custom/new')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[hsl(var(--primary))]/15 border border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/25"
            data-testid="make-your-own-btn">
            <Plus className="w-3.5 h-3.5" /> Make Your Own
          </button>
        </div>
        {customPortfolios.length === 0 ? (
          <div onClick={() => navigate('/portfolio/custom/new')}
            className="p-6 rounded-xl border-2 border-dashed border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/50 cursor-pointer text-center group" style={{ transition: 'border-color 0.2s' }}
            data-testid="create-first-portfolio">
            <Plus className="w-8 h-8 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))] mx-auto mb-2" style={{ transition: 'color 0.2s' }} />
            <p className="text-sm text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--foreground))]">Create your first custom portfolio</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Pick up to 10 stocks, set weights, track performance</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {customPortfolios.map(cp => {
              const cpPnl = cp.total_pnl || 0;
              const cpPnlPct = cp.total_pnl_pct || 0;
              return (
                <div key={cp.id} onClick={() => navigate(`/portfolio/custom/${cp.id}`)}
                  className="p-4 rounded-xl border border-[hsl(var(--primary))]/20 bg-gradient-to-br from-[hsl(var(--primary))]/5 to-transparent cursor-pointer hover:scale-[1.01]" style={{ transition: 'transform 0.15s' }}
                  data-testid={`custom-portfolio-${cp.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-semibold text-[hsl(var(--foreground))]">{cp.name}</h3>
                        <span className="text-[9px] bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] px-1.5 py-0.5 rounded font-mono">Custom</span>
                      </div>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{(cp.holdings || []).length} stocks | {cp.rebalance_count || 0}x rebalanced</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-mono font-bold text-[hsl(var(--foreground))]">
                        <IndianRupee className="w-3 h-3 inline" />{(cp.current_value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                      <p className={`text-sm font-mono ${cpPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {cpPnl >= 0 ? '+' : ''}{cpPnlPct.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-center mt-2 text-[hsl(var(--muted-foreground))]">
                    <span className="text-[10px] mr-1">View Details</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function UnconstructedCard({ type, strategies, BACKEND_URL }) {
  const cfg = strategies[type] || PORTFOLIO_STRATEGIES_FALLBACK[type] || {};
  const Icon = STRATEGY_ICONS[type] || BarChart3;
  const colors = STRATEGY_COLORS[type] || '';
  const [building, setBuilding] = useState(false);

  return (
    <div className={`p-4 rounded-xl border bg-gradient-to-br ${colors}`} data-testid={`portfolio-card-${type}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[hsl(var(--surface-1))] flex items-center justify-center">
            <Icon className="w-5 h-5 text-[hsl(var(--muted-foreground))]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[hsl(var(--foreground))]">{cfg.name || type.replace(/_/g, ' ')}</h3>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{building ? 'Construction in progress... ~2-3 min' : 'Not yet constructed'}</p>
          </div>
        </div>
        <button
          disabled={building}
          onClick={() => {
            setBuilding(true);
            fetch(`${BACKEND_URL}/api/portfolios/${type}/construct`, { method: 'POST' }).catch(() => {});
          }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-[hsl(var(--primary))]/15 border border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/25 disabled:opacity-50"
          data-testid={`construct-btn-${type}`}>
          {building ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
          {building ? 'Building...' : 'Construct Now'}
        </button>
      </div>
    </div>
  );
}

const PORTFOLIO_STRATEGIES_FALLBACK = {
  bespoke_forward_looking: { name: 'Bespoke Forward Looking' },
  quick_entry: { name: 'Quick Entry' },
  long_term: { name: 'Long Term Compounder' },
  swing: { name: 'Swing Trader' },
  alpha_generator: { name: 'Alpha Generator' },
  value_stocks: { name: 'Value Stocks' },
};

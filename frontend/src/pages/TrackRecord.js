import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Trophy, TrendingUp, TrendingDown, Target, ShieldAlert, BarChart3, Brain } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { useApi } from '../hooks/useApi';

const PIE_COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#6b7280'];

export default function TrackRecord() {
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const { getTrackRecord } = useApi();

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await getTrackRecord();
        setRecord(data);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-6 space-y-6 max-w-[1600px]">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const metrics = record?.metrics || {};
  const equityCurve = record?.equity_curve || [];
  const byAction = record?.by_action || {};
  const bySector = record?.by_sector || {};
  const byConfidence = record?.by_confidence || {};
  const streaks = record?.streaks || {};

  const hasData = record && record.closed_signals > 0;

  // Transform sector data for bar chart
  const sectorChartData = Object.entries(bySector).map(([sector, stats]) => ({
    sector,
    win_rate: stats.win_rate,
    avg_return: stats.avg_return,
    count: stats.count,
  })).sort((a, b) => b.avg_return - a.avg_return);

  // Action breakdown for pie chart
  const actionPieData = Object.entries(byAction).map(([action, stats]) => ({
    name: action,
    value: stats.count,
    win_rate: stats.win_rate,
  }));

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-[1600px]" data-testid="track-record-page">
      <div>
        <h1 className="font-display text-3xl font-bold flex items-center gap-3">
          <Trophy className="w-8 h-8 text-[hsl(var(--warning))]" />
          Track Record
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Historical performance of AI-generated signals
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Win Rate</p>
            <p className={`font-mono text-3xl font-bold mt-1 ${metrics.win_rate >= 50 ? 'text-up' : 'text-down'}`}>
              {metrics.win_rate != null ? `${metrics.win_rate}%` : '--'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Expectancy</p>
            <p className={`font-mono text-3xl font-bold mt-1 ${metrics.expectancy >= 0 ? 'text-up' : 'text-down'}`}>
              {metrics.expectancy != null ? `${metrics.expectancy}%` : '--'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Profit Factor</p>
            <p className="font-mono text-3xl font-bold mt-1 text-[hsl(var(--primary))]">
              {metrics.profit_factor != null ? metrics.profit_factor : '--'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Avg Win</p>
            <p className="font-mono text-3xl font-bold mt-1 text-up">
              {metrics.avg_win != null ? `+${metrics.avg_win}%` : '--'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Avg Loss</p>
            <p className="font-mono text-3xl font-bold mt-1 text-down">
              {metrics.avg_loss != null ? `${metrics.avg_loss}%` : '--'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-3 text-center">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Total Signals</p>
            <p className="font-mono text-lg font-bold">{record?.total_signals || 0}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-3 text-center">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Open</p>
            <p className="font-mono text-lg font-bold text-blue-400">{record?.open_signals || 0}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-3 text-center">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Total Return</p>
            <p className={`font-mono text-lg font-bold ${(metrics.total_return || 0) >= 0 ? 'text-up' : 'text-down'}`}>
              {metrics.total_return != null ? `${metrics.total_return}%` : '--'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-3 text-center">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Best Trade</p>
            <p className="font-mono text-lg font-bold text-up">{metrics.max_win != null ? `+${metrics.max_win}%` : '--'}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-3 text-center">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Worst Trade</p>
            <p className="font-mono text-lg font-bold text-down">{metrics.max_loss != null ? `${metrics.max_loss}%` : '--'}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-3 text-center">
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Win Streak</p>
            <p className="font-mono text-lg font-bold">{streaks.max_win_streak || 0}</p>
          </CardContent>
        </Card>
      </div>

      {/* Equity Curve */}
      {equityCurve.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-display">Equity Curve (Cumulative Returns)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={equityCurve} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(186, 92%, 42%)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(186, 92%, 42%)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }} tickFormatter={(t) => t.slice(5, 10)} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'hsl(222, 18%, 10%)', border: '1px solid hsl(222, 14%, 18%)', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(val, name) => [val + '%', name]}
                />
                <Area type="monotone" dataKey="cumulative" stroke="hsl(186, 92%, 42%)" fill="url(#equityGrad)" strokeWidth={2} name="Cumulative" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Sector */}
        {sectorChartData.length > 0 && (
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-display">Performance by Sector</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={sectorChartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="sector" tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }} />
                  <YAxis tick={{ fontSize: 10, fill: 'hsl(215, 16%, 50%)' }} />
                  <Tooltip contentStyle={{ backgroundColor: 'hsl(222, 18%, 10%)', border: '1px solid hsl(222, 14%, 18%)', borderRadius: '8px', fontSize: '12px' }} />
                  <Bar dataKey="avg_return" name="Avg Return %" fill="hsl(186, 92%, 42%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* By Confidence */}
        {Object.keys(byConfidence).length > 0 && (
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-display">Performance by Confidence Band</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(byConfidence).map(([band, stats]) => (
                  <div key={band} className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{band}</span>
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">{stats.count} signals</span>
                    </div>
                    <div className="flex gap-4">
                      <span className={`text-sm font-mono font-bold ${stats.win_rate >= 50 ? 'text-up' : 'text-down'}`}>
                        WR: {stats.win_rate}%
                      </span>
                      <span className={`text-sm font-mono font-bold ${stats.avg_return >= 0 ? 'text-up' : 'text-down'}`}>
                        Avg: {stats.avg_return}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-[hsl(var(--surface-3))] rounded-full mt-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${stats.win_rate}%`,
                          backgroundColor: stats.win_rate >= 50 ? 'hsl(142, 70%, 45%)' : 'hsl(0, 72%, 52%)',
                          transition: 'width 0.5s ease',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* No data state */}
      {!hasData && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-12 text-center">
            <Trophy className="w-16 h-16 text-[hsl(var(--muted-foreground))] mx-auto mb-4 opacity-20" />
            <h3 className="font-display text-xl font-semibold mb-2">No Closed Signals Yet</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Generate signals and evaluate them to build your track record. As signals hit targets, stops, or expire, the AI will learn from outcomes.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4" data-testid="sebi-disclaimer-alert">
        <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
          <strong>Disclaimer:</strong> Track record is based on AI-generated signals for educational purposes. Past results do not guarantee future performance. Always do your own research.
        </p>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/ui/card';
import { ScrollArea } from '../components/ui/scroll-area';
import { Shield, RefreshCw, Loader2, Search, User, Clock, Activity, Filter, AlertTriangle, Lock } from 'lucide-react';
import { getUser } from '../components/TOTPGate';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ACTION_COLORS = {
  'Logged in': 'bg-emerald-500/15 text-emerald-400',
  'Failed login': 'bg-red-500/15 text-red-400',
  'Set new password': 'bg-amber-500/15 text-amber-400',
  'Triggered portfolio rebuild': 'bg-red-500/15 text-red-400',
  'Ran God Mode scan': 'bg-violet-500/15 text-violet-400',
  'Generated signal': 'bg-cyan-500/15 text-cyan-400',
  'Created custom portfolio': 'bg-emerald-500/15 text-emerald-400',
  'Rebalanced custom portfolio': 'bg-amber-500/15 text-amber-400',
  'Deleted custom portfolio': 'bg-red-500/15 text-red-400',
  'Toggled daemon': 'bg-amber-500/15 text-amber-400',
  'Constructed portfolio': 'bg-emerald-500/15 text-emerald-400',
};

function getActionColor(action) {
  for (const [key, cls] of Object.entries(ACTION_COLORS)) {
    if (action?.includes(key)) return cls;
  }
  return 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]';
}

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filterUser, setFilterUser] = useState('');
  const [filterAction, setFilterAction] = useState('');
  const [error, setError] = useState(null);

  const user = getUser();
  const isSuperadmin = user?.superadmin || user?.sub === 'somnath.dey@smifs.com';

  const fetchLogs = useCallback(async () => {
    const token = localStorage.getItem('bmia_session_token');
    if (!token) return;
    try {
      const params = new URLSearchParams({ limit: '200' });
      if (filterUser) params.set('user', filterUser);
      if (filterAction) params.set('action', filterAction);

      const res = await fetch(`${BACKEND_URL}/api/audit-log?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await res.json();
      if (d.error) { setError(d.error); } else {
        setLogs(d.logs || []);
        setUsers(d.users || []);
        setError(null);
      }
    } catch { setError('Failed to load audit log'); }
    setLoading(false);
  }, [filterUser, filterAction]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const handleRefresh = async () => { setRefreshing(true); await fetchLogs(); setRefreshing(false); };

  if (!isSuperadmin) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-64 gap-3" data-testid="audit-restricted">
        <Lock className="w-8 h-8 text-red-400" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">Superadmin access required</p>
      </div>
    );
  }

  // Group logs by date
  const grouped = {};
  logs.forEach(log => {
    const date = log.timestamp?.split('T')[0] || 'Unknown';
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(log);
  });

  return (
    <div className="p-3 sm:p-6 max-w-5xl mx-auto space-y-4" data-testid="audit-log-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-display font-bold text-[hsl(var(--foreground))]">Audit Log</h1>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{logs.length} events recorded</p>
        </div>
        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-50 self-start sm:self-auto"
          data-testid="refresh-audit-btn">
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex items-center gap-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2 flex-1">
          <User className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />
          <select value={filterUser} onChange={e => setFilterUser(e.target.value)}
            className="bg-transparent text-xs text-[hsl(var(--foreground))] outline-none flex-1"
            data-testid="filter-user">
            <option value="">All users</option>
            {users.map(u => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2 flex-1">
          <Search className="w-3.5 h-3.5 text-[hsl(var(--muted-foreground))]" />
          <input type="text" value={filterAction} onChange={e => setFilterAction(e.target.value)}
            placeholder="Filter by action..."
            className="bg-transparent text-xs text-[hsl(var(--foreground))] outline-none flex-1 placeholder:text-[hsl(var(--muted-foreground))]"
            data-testid="filter-action" />
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--primary))]" />
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
          <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No audit events yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([date, dayLogs]) => (
            <div key={date}>
              <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-2 font-mono">
                {new Date(date + 'T00:00:00Z').toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
              </p>
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] overflow-hidden divide-y divide-[hsl(var(--border))]/30">
                {dayLogs.map((log, i) => {
                  const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--';
                  const statusOk = log.status_code >= 200 && log.status_code < 400;
                  return (
                    <div key={i} className="flex items-center gap-3 px-3 py-2.5 hover:bg-[hsl(var(--surface-2))]" data-testid={`audit-entry-${i}`}>
                      <div className="w-16 flex-shrink-0">
                        <p className="text-[10px] font-mono text-[hsl(var(--muted-foreground))]">{time}</p>
                      </div>
                      <div className="w-36 flex-shrink-0 truncate">
                        <p className="text-xs font-medium text-[hsl(var(--foreground))] truncate">{log.user_name || log.user_email?.split('@')[0] || 'anon'}</p>
                        <p className="text-[9px] text-[hsl(var(--muted-foreground))] truncate">{log.user_email}</p>
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${getActionColor(log.action)}`}>
                          {log.action}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-[9px] font-mono text-[hsl(var(--muted-foreground))]">{log.method}</span>
                        <span className={`text-[9px] font-mono ${statusOk ? 'text-emerald-400' : 'text-red-400'}`}>{log.status_code}</span>
                      </div>
                    </div>
                  );
                })}
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

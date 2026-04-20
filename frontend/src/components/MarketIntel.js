import React, { useState, useEffect, useCallback } from 'react';
import {
  Newspaper, Calendar, Users, Scale, Target, ExternalLink,
  TrendingUp, TrendingDown, Activity, Loader2, RefreshCw,
} from 'lucide-react';
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis,
  Tooltip, BarChart, Bar, Cell,
} from 'recharts';
import { ResponsiveContainer } from './layout/SafeResponsiveContainer';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

const API = process.env.REACT_APP_BACKEND_URL || '';
const nf = (v, d = 2) => v == null ? '-' : Number(v).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v) => v == null ? '-' : `${v > 0 ? '+' : ''}${Number(v).toFixed(2)}%`;
const pctColor = (v) => v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-[hsl(var(--muted-foreground))]';

function SectionTitle({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="flex items-end justify-between mb-3">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-[hsl(var(--primary))]" />
        <div>
          <h3 className="text-sm font-display font-semibold tracking-wide">{title}</h3>
          {subtitle && <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

// ─── 1. Market Movers scatter ─────────────────────────────────────────
function MoversScatter() {
  const [d, setD] = useState(null);
  useEffect(() => {
    fetch(`${API}/api/big-market/movers`).then(r => r.json()).then(setD).catch(() => setD({}));
  }, []);
  if (!d) return <Skel height={320} />;
  const rows = [
    ...(d.gainers || []).map(r => ({ ...r, fill: '#10b981' })),
    ...(d.losers || []).map(r => ({ ...r, fill: '#ef4444' })),
    ...(d.high_volume || []).map(r => ({ ...r, fill: '#06b6d4' })),
  ].filter(r => r.pct_change !== undefined && r.volume !== undefined);
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="movers-scatter-card">
      <SectionTitle icon={Activity} title="Market Movers" subtitle={`${rows.length} stocks · x: % change · y: volume · size: market cap`} />
      {rows.length === 0 ? <Empty /> : (
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
            <XAxis type="number" dataKey="pct_change" name="% change" tickFormatter={(v) => `${v}%`} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
            <YAxis type="number" dataKey="volume" name="Volume" tickFormatter={(v) => v >= 1e7 ? `${(v / 1e7).toFixed(1)}Cr` : v >= 1e5 ? `${(v / 1e5).toFixed(0)}L` : v} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
            <ZAxis type="number" dataKey="market_cap_cr" range={[30, 400]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ background: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: 6, fontSize: 11 }}
              formatter={(value, name) => name === '% change' ? pct(value) : name === 'Volume' ? nf(value, 0) : value}
              labelFormatter={() => ''}
              content={({ payload }) => payload?.[0]?.payload ? (
                <div className="bg-[hsl(var(--popover))] border border-[hsl(var(--border))] rounded p-2 text-xs">
                  <div className="font-semibold">{payload[0].payload.symbol}</div>
                  <div className="text-[10px] text-[hsl(var(--muted-foreground))]">{payload[0].payload.company}</div>
                  <div className={`font-mono ${pctColor(payload[0].payload.pct_change)}`}>{pct(payload[0].payload.pct_change)}</div>
                  <div className="font-mono text-[10px]">Vol {nf(payload[0].payload.volume, 0)}</div>
                </div>
              ) : null}
            />
            <Scatter name="Stocks" data={rows}>
              {rows.map((r, i) => <Cell key={i} fill={r.fill} />)}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      )}
      <div className="flex items-center gap-4 mt-2 text-[10px] text-[hsl(var(--muted-foreground))]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />Gainers</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />Losers</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" />High volume</span>
      </div>
    </Card>
  );
}

// ─── 2. FII / DII flows ──────────────────────────────────────────────
function FiiDii() {
  const [d, setD] = useState(null);
  useEffect(() => { fetch(`${API}/api/big-market/fii-dii`).then(r => r.json()).then(setD).catch(() => setD({})); }, []);
  if (!d) return <Skel height={220} />;
  // API shape: { flows: [{ date, fii_net, dii_net, fii_long_contracts, fii_short_contracts, ... }], updated_at }
  // Take the most recent day; flows are ordered chronologically.
  const flows = Array.isArray(d.flows) ? d.flows : [];
  const latest = flows.length ? flows[flows.length - 1] : {};
  const fiiFoNet = (latest.fii_long_contracts || 0) - (latest.fii_short_contracts || 0);
  const rows = [
    { label: 'FII Net', value: latest.fii_net ?? d.fii_cash_net ?? null, unit: '₹ Cr' },
    { label: 'DII Net', value: latest.dii_net ?? d.dii_cash_net ?? null, unit: '₹ Cr' },
    { label: 'FII Buy', value: latest.fii_buy ?? null, unit: '₹ Cr' },
    { label: 'FII F&O Net', value: flows.length ? fiiFoNet : null, unit: 'Contracts' },
  ].filter(r => r.value !== null && r.value !== undefined);
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="fii-dii-card">
      <SectionTitle icon={Users} title="Institutional Flows" subtitle={latest.display_date || latest.date || 'Latest available'} />
      {rows.length === 0 ? <Empty /> : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {rows.map((r, i) => (
            <div key={i} className="bg-[hsl(var(--surface-2))] rounded-lg p-3" data-testid={`fii-dii-${r.label.toLowerCase().replace(/\s|\/|&/g, '-')}`}>
              <div className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider">{r.label}</div>
              <div className={`text-lg font-mono font-bold ${pctColor(r.value)}`}>{r.value > 0 ? '+' : ''}{nf(r.value, 0)}</div>
              <div className="text-[9px] text-[hsl(var(--muted-foreground))]">{r.unit}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── 3. Earnings Calendar ────────────────────────────────────────────
function EarningsCalendar() {
  const [d, setD] = useState(null);
  useEffect(() => { fetch(`${API}/api/big-market/earnings-calendar?days=14`).then(r => r.json()).then(setD).catch(() => setD([])); }, []);
  if (!d) return <Skel height={300} />;
  // Group by date
  const grouped = {};
  (d || []).forEach(e => { (grouped[e.date] = grouped[e.date] || []).push(e); });
  const dates = Object.keys(grouped).sort();
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="earnings-calendar-card">
      <SectionTitle icon={Calendar} title="Earnings & Events" subtitle={`Next 14 days · ${(d || []).length} events`} />
      {dates.length === 0 ? <Empty /> : (
        <div className="max-h-[380px] overflow-y-auto space-y-3">
          {dates.map(date => (
            <div key={date}>
              <div className="sticky top-0 bg-[hsl(var(--card))] text-[11px] font-semibold text-[hsl(var(--primary))] uppercase tracking-wider mb-1.5 py-1">{date}</div>
              <div className="space-y-1">
                {grouped[date].slice(0, 15).map((e, i) => (
                  <div key={i} className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-[hsl(var(--surface-2))] text-xs" data-testid={`earnings-event-${e.symbol}`}>
                    <Badge variant="outline" className="text-[9px] px-1.5 py-0 min-w-0 shrink-0">{e.event_type?.slice(0, 18) || 'Event'}</Badge>
                    <span className="font-semibold text-[hsl(var(--foreground))] shrink-0">{e.symbol}</span>
                    <span className="text-[hsl(var(--muted-foreground))] truncate">{e.company}</span>
                  </div>
                ))}
                {grouped[date].length > 15 && <div className="text-[10px] text-[hsl(var(--muted-foreground))] pl-2.5">+ {grouped[date].length - 15} more</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── 4. Put-Call Ratio ────────────────────────────────────────────────
function PCR() {
  const [d, setD] = useState(null);
  useEffect(() => { fetch(`${API}/api/big-market/pcr`).then(r => r.json()).then(setD).catch(() => setD({})); }, []);
  if (!d) return <Skel height={180} />;
  const c = d.current || {};
  const items = [
    { label: 'NIFTY', value: c.nifty?.pcr ?? c.nifty_pcr, signal: c.nifty?.sentiment, expiry: c.nifty?.expiry },
    { label: 'BANK NIFTY', value: c.banknifty?.pcr ?? c.banknifty_pcr, signal: c.banknifty?.sentiment, expiry: c.banknifty?.expiry },
  ];
  const interpret = (v) => {
    if (v == null) return null;
    if (v >= 1.3) return { txt: 'Oversold', color: 'text-emerald-400' };
    if (v >= 1.0) return { txt: 'Bearish', color: 'text-amber-400' };
    if (v >= 0.7) return { txt: 'Neutral', color: 'text-[hsl(var(--muted-foreground))]' };
    return { txt: 'Bullish · Overbought', color: 'text-red-400' };
  };
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="pcr-card">
      <SectionTitle icon={Scale} title="Put-Call Ratio" subtitle="OI-based · derivatives sentiment" />
      <div className="grid grid-cols-2 gap-3">
        {items.map((r, i) => {
          const sig = interpret(r.value);
          return (
            <div key={i} className="bg-[hsl(var(--surface-2))] rounded-lg p-4" data-testid={`pcr-${r.label.toLowerCase().replace(/\s/g, '-')}`}>
              <div className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider">{r.label}</div>
              <div className="text-2xl font-mono font-bold text-[hsl(var(--foreground))]">{r.value != null ? nf(r.value, 2) : '-'}</div>
              {sig && <div className={`text-[10px] ${sig.color} font-semibold uppercase tracking-wider mt-1`}>{sig.txt}</div>}
              {r.expiry && <div className="text-[9px] text-[hsl(var(--muted-foreground))] font-mono mt-0.5">Exp: {r.expiry}</div>}
            </div>
          );
        })}
      </div>
      <div className="mt-3 text-[10px] text-[hsl(var(--muted-foreground))]">
        PCR &gt; 1.3 oversold · 1.0–1.3 bearish · 0.7–1.0 neutral · &lt; 0.7 overbought
      </div>
    </Card>
  );
}

// ─── 5. Analyst Estimates ─────────────────────────────────────────────
function AnalystEstimates() {
  const [sym, setSym] = useState('RELIANCE');
  const [d, setD] = useState(null);
  const load = useCallback((s) => {
    setD(null);
    fetch(`${API}/api/big-market/analyst-estimates/${encodeURIComponent(s)}`).then(r => r.json()).then(setD).catch(() => setD({}));
  }, []);
  useEffect(() => { load(sym); }, [load, sym]);
  const rec = d?.recommendations;
  const recData = rec ? [
    { name: 'Strong Buy', value: rec.strong_buy, fill: '#059669' },
    { name: 'Buy', value: rec.buy, fill: '#10b981' },
    { name: 'Hold', value: rec.hold, fill: '#eab308' },
    { name: 'Sell', value: rec.sell, fill: '#f97316' },
    { name: 'Strong Sell', value: rec.strong_sell, fill: '#ef4444' },
  ] : [];
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="analyst-estimates-card">
      <SectionTitle icon={Target} title={`Analyst Estimates · ${d?.symbol || sym}`}>
        <form onSubmit={(e) => { e.preventDefault(); load(sym); }} className="flex items-center gap-1">
          <input
            value={sym}
            onChange={(e) => setSym(e.target.value.toUpperCase())}
            placeholder="TICKER"
            className="h-7 px-2 text-xs rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] w-28 font-mono uppercase"
            data-testid="analyst-ticker-input"
          />
          <button type="submit" className="h-7 px-2.5 text-[10px] rounded bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-semibold" data-testid="analyst-load-btn">GO</button>
        </form>
      </SectionTitle>
      {!d ? <Skel height={180} /> : (
        Object.keys(d).length <= 1 ? <Empty note="No estimates available for this ticker." /> : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
              {[
                { k: 'cmp', label: 'CMP', prefix: '₹', dec: 2 },
                { k: 'pe', label: 'P/E', dec: 1 },
                { k: 'eps', label: 'EPS', prefix: '₹', dec: 2 },
                { k: 'roe', label: 'ROE', suffix: '%', dec: 1 },
                { k: 'market_cap_cr', label: 'Mcap', suffix: ' Cr', dec: 0 },
                { k: 'book_value', label: 'Book', prefix: '₹', dec: 2 },
                { k: 'div_yield', label: 'Yield', suffix: '%', dec: 2 },
              ].filter(m => d[m.k] != null).map(m => (
                <div key={m.k} className="bg-[hsl(var(--surface-2))] rounded p-2" data-testid={`estimate-${m.k}`}>
                  <div className="text-[9px] uppercase text-[hsl(var(--muted-foreground))]">{m.label}</div>
                  <div className="text-sm font-mono font-bold">{m.prefix || ''}{nf(d[m.k], m.dec)}{m.suffix || ''}</div>
                </div>
              ))}
            </div>
            {recData.length > 0 && (
              <div>
                <div className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase mb-1">Consensus ratings</div>
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={recData} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="name" width={80} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {recData.map((r, i) => <Cell key={i} fill={r.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )
      )}
    </Card>
  );
}

// ─── 6. News ─────────────────────────────────────────────────────────
function News() {
  const [d, setD] = useState(null);
  const load = useCallback(() => fetch(`${API}/api/big-market/news?limit=25`).then(r => r.json()).then(setD).catch(() => setD([])), []);
  useEffect(() => { load(); const id = setInterval(load, 300000); return () => clearInterval(id); }, [load]);
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] p-4" data-testid="news-card">
      <SectionTitle icon={Newspaper} title="Market News" subtitle={`${(d || []).length} headlines · auto-refresh 5m`}>
        <button onClick={load} className="text-[10px] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] flex items-center gap-1" data-testid="news-refresh-btn">
          <RefreshCw className="w-3 h-3" />
        </button>
      </SectionTitle>
      {!d ? <Skel height={300} /> : d.length === 0 ? <Empty note="News feed warming up…" /> : (
        <div className="max-h-[400px] overflow-y-auto divide-y divide-[hsl(var(--border))]">
          {d.map((n, i) => (
            <a
              key={i}
              href={n.url}
              target="_blank"
              rel="noopener noreferrer"
              data-testid={`news-item-${i}`}
              className="flex items-start gap-2 px-2 py-2.5 hover:bg-[hsl(var(--surface-2))] group"
              style={{ transition: 'background-color 0.15s ease' }}
            >
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[hsl(var(--foreground))] leading-snug line-clamp-2 group-hover:text-[hsl(var(--primary))]">{n.title}</div>
                <div className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{n.published_at?.slice(0, 16) || n.category}</div>
              </div>
              <ExternalLink className="w-3 h-3 text-[hsl(var(--muted-foreground))] mt-1 shrink-0 opacity-0 group-hover:opacity-100" />
            </a>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────
const Skel = ({ height }) => (
  <div className="flex items-center justify-center" style={{ height }}>
    <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--muted-foreground))]" />
  </div>
);
const Empty = ({ note = 'No data yet.' }) => (
  <div className="text-center py-10 text-xs text-[hsl(var(--muted-foreground))]">{note}</div>
);

export default function MarketIntel() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="market-intel-grid">
      <div className="lg:col-span-2"><MoversScatter /></div>
      <FiiDii />
      <PCR />
      <EarningsCalendar />
      <AnalystEstimates />
      <div className="lg:col-span-2"><News /></div>
    </div>
  );
}

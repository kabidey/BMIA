import React, { useEffect, useMemo, useRef, useState } from 'react';
import { X, Network, Loader2, Info, Search, Filter, Maximize2 } from 'lucide-react';
import ForceGraph3D from 'react-force-graph-3d';

// Color palette by source / entity type
const PALETTE = {
  nse: '#38bdf8',        // sky-400
  bse: '#f59e0b',        // amber-500
  sebi: '#10b981',       // emerald-500
  entity: '#c084fc',     // purple-400
  // Entity sub-types
  REGULATION: '#f472b6', // pink-400
  COMPANY: '#fbbf24',    // amber-400
  PERSON: '#60a5fa',     // blue-400
  CONCEPT: '#a78bfa',    // violet-400
  DATE: '#94a3b8',       // slate-400
  EVENT: '#fb7185',      // rose-400
};

const getNodeColor = (node) => {
  if (node.source === 'entity') return PALETTE[node.entity_type] || PALETTE.entity;
  return PALETTE[node.source] || '#9ca3af';
};

const getLinkColor = (link) => {
  if (link.type === 'entity') return 'rgba(192,132,252,0.35)';
  if (link.type === 'entity-rel') return 'rgba(244,114,182,0.55)';
  if (link.type === 'regulation') return 'rgba(16,185,129,0.35)';
  if (link.type === 'temporal') return 'rgba(148,163,184,0.25)';
  return 'rgba(156,163,175,0.3)';
};

export default function ComplianceGraph3D({
  open,
  onClose,
  subgraph = null,
  loading = false,
  title = '3D Compliance Graph',
  onNodeClick,
}) {
  const fgRef = useRef(null);
  const [hovered, setHovered] = useState(null);
  const [selected, setSelected] = useState(null);
  const [sourceFilter, setSourceFilter] = useState({ nse: true, bse: true, sebi: true, entity: true });
  const [dim, setDim] = useState({ w: 0, h: 0 });

  const filteredData = useMemo(() => {
    if (!subgraph) return { nodes: [], links: [] };
    const activeSources = Object.keys(sourceFilter).filter((k) => sourceFilter[k]);
    const keep = new Set(subgraph.nodes.filter((n) => activeSources.includes(n.source)).map((n) => n.id));
    // react-force-graph may mutate e.source/e.target into node objects after first
    // render. Normalise back to string ids via the object's id property.
    const sid = (x) => (typeof x === 'object' && x ? x.id : x);
    return {
      nodes: subgraph.nodes.filter((n) => keep.has(n.id)),
      links: subgraph.edges
        .filter((e) => keep.has(sid(e.source)) && keep.has(sid(e.target)))
        .map((e) => ({ ...e, source: sid(e.source), target: sid(e.target) })),
    };
  }, [subgraph, sourceFilter]);

  useEffect(() => {
    if (!open) return;
    const update = () => setDim({ w: window.innerWidth, h: window.innerHeight });
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, [open]);

  // Zoom to fit after initial render
  useEffect(() => {
    if (!open || !fgRef.current || filteredData.nodes.length === 0) return;
    const t = setTimeout(() => {
      try { fgRef.current?.zoomToFit(600, 120); } catch {}
    }, 700);
    return () => clearTimeout(t);
  }, [open, filteredData.nodes.length]);

  if (!open) return null;

  const counts = filteredData.nodes.reduce((acc, n) => {
    acc[n.source] = (acc[n.source] || 0) + 1;
    return acc;
  }, {});

  return (
    <div
      data-testid="compliance-graph-3d"
      className="fixed inset-0 z-[60] bg-black/85 backdrop-blur-sm flex flex-col"
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3 bg-[hsl(var(--surface-1))]/95 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))]/15 flex items-center justify-center">
            <Network className="w-4 h-4 text-[hsl(var(--primary))]" />
          </div>
          <div>
            <h2 className="text-sm font-display font-semibold text-[hsl(var(--foreground))]">{title}</h2>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">
              {filteredData.nodes.length} nodes · {filteredData.links.length} edges
              {subgraph?.nodes.some((n) => n.seed) && ' · seeds highlighted'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Source filters */}
          {Object.entries(sourceFilter).map(([src, on]) => (
            <button
              key={src}
              onClick={() => setSourceFilter((p) => ({ ...p, [src]: !p[src] }))}
              data-testid={`graph-filter-${src}`}
              className={`px-2.5 py-1 rounded-md text-[10px] font-medium uppercase tracking-wider border ${on ? 'text-white' : 'text-gray-500'}`}
              style={{
                backgroundColor: on ? `${PALETTE[src]}22` : 'transparent',
                borderColor: on ? `${PALETTE[src]}88` : 'rgb(75,85,99)',
                transition: 'background-color 0.15s ease',
              }}
            >
              <span className="inline-block w-1.5 h-1.5 rounded-full mr-1.5" style={{ backgroundColor: PALETTE[src] }} />
              {src} {counts[src] ? `· ${counts[src]}` : ''}
            </button>
          ))}
          <button
            onClick={() => fgRef.current?.zoomToFit(600, 120)}
            data-testid="graph-zoom-fit"
            className="w-8 h-8 rounded-md hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
            title="Zoom to fit"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            data-testid="graph-close-btn"
            className="w-8 h-8 rounded-md hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main graph */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-center gap-3 text-[hsl(var(--muted-foreground))]">
              <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--primary))]" />
              <span className="text-sm">Building knowledge graph...</span>
            </div>
          </div>
        ) : filteredData.nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-[hsl(var(--muted-foreground))]">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No graph data for this query.</p>
              <p className="text-[11px] mt-1 opacity-70">Try broader terms or toggle a source filter above.</p>
            </div>
          </div>
        ) : (
          <ForceGraph3D
            ref={fgRef}
            graphData={filteredData}
            width={dim.w}
            height={dim.h - 56}
            backgroundColor="rgba(5,8,20,1)"
            nodeLabel={(n) => `<div style="background:rgba(8,10,24,0.95);padding:8px 10px;border:1px solid rgba(120,120,180,0.4);border-radius:6px;max-width:320px;font-family:Inter,sans-serif"><div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:${getNodeColor(n)};margin-bottom:4px">${n.source === 'entity' ? n.entity_type : n.source} ${n.category ? '· ' + n.category : ''}${n.date ? ' · ' + n.date : ''}</div><div style="font-size:12px;color:#f1f5f9;line-height:1.35">${(n.label || '').replace(/</g, '&lt;')}</div>${(n.tags || []).length ? '<div style="font-size:9px;color:#94a3b8;margin-top:6px">' + n.tags.join(' · ') + '</div>' : ''}</div>`}
            nodeColor={getNodeColor}
            nodeVal={(n) => (n.seed ? 8 : n.val || 2)}
            nodeOpacity={0.92}
            nodeResolution={14}
            linkColor={getLinkColor}
            linkWidth={(l) => (l.type === 'entity-rel' ? 1.2 : 0.5)}
            linkDirectionalParticles={(l) => (l.type === 'entity-rel' ? 2 : 0)}
            linkDirectionalParticleSpeed={0.008}
            onNodeHover={setHovered}
            onNodeClick={(n) => {
              setSelected(n);
              onNodeClick?.(n);
              // Smoothly focus on clicked node
              const distance = 120;
              const distRatio = 1 + distance / Math.hypot(n.x || 1, n.y || 1, n.z || 1);
              fgRef.current?.cameraPosition(
                { x: (n.x || 0) * distRatio, y: (n.y || 0) * distRatio, z: (n.z || 0) * distRatio },
                n, 800,
              );
            }}
            onBackgroundClick={() => setSelected(null)}
            warmupTicks={40}
            cooldownTicks={100}
            enableNodeDrag={true}
          />
        )}
      </div>

      {/* Selected node panel */}
      {selected && (
        <div
          data-testid="graph-selected-panel"
          className="absolute bottom-4 left-4 right-4 md:right-auto md:max-w-md p-4 rounded-xl bg-[hsl(var(--surface-1))]/95 border border-[hsl(var(--border))] shadow-2xl backdrop-blur-md"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider"
                  style={{
                    backgroundColor: `${getNodeColor(selected)}22`,
                    color: getNodeColor(selected),
                  }}
                >
                  {selected.source === 'entity' ? selected.entity_type : selected.source}
                </span>
                {selected.category && selected.source !== 'entity' && (
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{selected.category}</span>
                )}
                {selected.date && (
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">{selected.date}</span>
                )}
              </div>
              <h3 className="text-sm font-medium text-[hsl(var(--foreground))] leading-snug">
                {selected.label}
              </h3>
              {selected.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {selected.tags.map((t) => (
                    <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={() => setSelected(null)}
              className="w-6 h-6 rounded hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {selected.url && (
            <a
              href={selected.url}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="graph-open-pdf"
              className="mt-3 inline-flex items-center gap-1 text-[11px] text-[hsl(var(--primary))] hover:underline"
            >
              Open original document →
            </a>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 right-4 p-3 rounded-lg bg-[hsl(var(--surface-1))]/80 border border-[hsl(var(--border))] backdrop-blur-md">
        <div className="text-[9px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-2">Legend</div>
        <div className="space-y-1">
          {['nse', 'bse', 'sebi', 'entity'].map((k) => (
            <div key={k} className="flex items-center gap-2 text-[10px] text-[hsl(var(--muted-foreground))]">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: PALETTE[k] }} />
              <span className="uppercase tracking-wider">{k === 'entity' ? 'Entity' : k}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

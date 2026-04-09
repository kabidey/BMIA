import React from 'react';
import { RefreshCw } from 'lucide-react';

export function TerminalPanel({ title, subtitle, children, className = '', updatedAt, loading = false }) {
  return (
    <div className={`rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]/70 backdrop-blur-[2px] ${className}`}>
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-display tracking-wide text-[hsl(var(--foreground))]/90">{title}</h3>
          {subtitle && <span className="text-[11px] text-[hsl(var(--muted-foreground))] font-mono">{subtitle}</span>}
        </div>
        <div className="flex items-center gap-2">
          {loading && <RefreshCw className="w-3 h-3 text-[hsl(var(--primary))] animate-spin" />}
          {updatedAt && (
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
              {new Date(updatedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
        </div>
      </div>
      <div className="p-3">
        {children}
      </div>
    </div>
  );
}

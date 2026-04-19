import React from 'react';
import { X, Scale, ExternalLink } from 'lucide-react';
import ComplianceResearchPanel from './ComplianceResearchPanel';

export default function ComplianceModal({ open, onClose }) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm flex items-stretch justify-center"
      onClick={onClose}
      data-testid="compliance-modal-overlay"
    >
      <div
        className="relative w-full max-w-6xl m-2 sm:m-6 rounded-xl bg-[hsl(var(--background))] border border-[hsl(var(--border))] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
        data-testid="compliance-modal"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[hsl(var(--primary))]/15 flex items-center justify-center">
              <Scale className="w-4 h-4 text-[hsl(var(--primary))]" />
            </div>
            <div>
              <div className="text-sm font-display font-semibold">Compliance Research</div>
              <div className="text-[10px] text-[hsl(var(--muted-foreground))]">NSE · BSE · SEBI circulars</div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <a
              href="/compliance"
              className="flex items-center gap-1 text-[11px] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] px-2 py-1 rounded"
              data-testid="compliance-modal-open-full"
            >
              Open full page <ExternalLink className="w-3 h-3" />
            </a>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--muted-foreground))]"
              data-testid="compliance-modal-close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <ComplianceResearchPanel compact />
        </div>
      </div>
    </div>
  );
}

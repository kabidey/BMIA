import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Upload, FileArchive, Loader2, CheckCircle2, AlertCircle, Clock, RefreshCw, Info } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SOURCES = [
  { id: 'nse', label: 'NSE', color: 'text-sky-400', dot: 'bg-sky-500' },
  { id: 'bse', label: 'BSE', color: 'text-amber-400', dot: 'bg-amber-500' },
  { id: 'sebi', label: 'SEBI', color: 'text-emerald-400', dot: 'bg-emerald-500' },
];

const STATUS_STYLE = {
  queued: { cls: 'bg-sky-500/15 text-sky-400 border-sky-500/30', Icon: Clock },
  running: { cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30', Icon: Loader2 },
  done: { cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', Icon: CheckCircle2 },
  failed: { cls: 'bg-red-500/15 text-red-400 border-red-500/30', Icon: AlertCircle },
};

const fmtTime = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
};

export default function ComplianceBulkUploadModal({ open, onClose, onCompleted }) {
  const [source, setSource] = useState('sebi');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const pollRef = useRef(null);
  const inputRef = useRef(null);

  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const r = await fetch(`${BACKEND_URL}/api/compliance/bulk-upload?limit=15`);
      if (r.ok) {
        const data = await r.json();
        setJobs(data.jobs || []);
      }
    } catch {}
    setLoadingJobs(false);
  }, []);

  const pollJob = useCallback(async (jobId) => {
    try {
      const r = await fetch(`${BACKEND_URL}/api/compliance/bulk-upload/${jobId}`);
      if (!r.ok) return;
      const data = await r.json();
      setJobs(prev => {
        const idx = prev.findIndex(j => j.job_id === jobId);
        if (idx === -1) return [data, ...prev];
        const next = [...prev];
        next[idx] = data;
        return next;
      });
      if (data.status === 'done') {
        toast.success(`Bulk upload complete — ${data.ingested} ingested`, {
          description: `${data.source.toUpperCase()} · ${data.skipped || 0} skipped · ${data.failed || 0} failed`,
          duration: 8000,
        });
        setActiveJobId(null);
        clearInterval(pollRef.current);
        pollRef.current = null;
        onCompleted?.();
      } else if (data.status === 'failed') {
        toast.error('Bulk upload failed', {
          description: data.error || 'Unknown error',
          duration: 8000,
        });
        setActiveJobId(null);
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {}
  }, [onCompleted]);

  useEffect(() => {
    if (!open) return;
    loadJobs();
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [open, loadJobs]);

  useEffect(() => {
    if (!activeJobId) return;
    pollJob(activeJobId);
    pollRef.current = setInterval(() => pollJob(activeJobId), 3000);
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [activeJobId, pollJob]);

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.zip')) {
      toast.error('Please select a .zip archive of PDFs');
      return;
    }
    setFile(f);
  };

  const handleUpload = async () => {
    if (!file || uploading) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('source', source);
    fd.append('file', file);
    toast.loading('Uploading archive...', { id: 'bulk-upload' });
    try {
      const r = await fetch(`${BACKEND_URL}/api/compliance/bulk-upload`, {
        method: 'POST',
        body: fd,
      });
      const data = await r.json();
      if (!r.ok) {
        throw new Error(data.detail || `HTTP ${r.status}`);
      }
      toast.success('Upload queued — processing PDFs in background', {
        id: 'bulk-upload',
        description: `Job ${data.job_id.slice(0, 8)} · ${data.size_mb} MB`,
      });
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      setActiveJobId(data.job_id);
      loadJobs();
    } catch (err) {
      toast.error('Upload failed', {
        id: 'bulk-upload',
        description: String(err?.message || err),
      });
    }
    setUploading(false);
  };

  if (!open) return null;

  const fileSizeMB = file ? (file.size / (1024 * 1024)).toFixed(1) : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      data-testid="bulk-upload-modal"
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      <div className="w-full max-w-2xl max-h-[90vh] flex flex-col rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))]/15 flex items-center justify-center">
              <FileArchive className="w-4 h-4 text-[hsl(var(--primary))]" />
            </div>
            <div>
              <h2 className="text-sm font-display font-semibold text-[hsl(var(--foreground))]">Bulk circular archive</h2>
              <p className="text-[11px] text-[hsl(var(--muted-foreground))]">Upload a ZIP of PDFs to bypass upstream rate limits</p>
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="bulk-upload-close-btn"
            className="w-8 h-8 rounded-md hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Filename hint */}
          <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
            <Info className="w-3.5 h-3.5 text-[hsl(var(--primary))] mt-0.5 shrink-0" />
            <div className="text-[11px] text-[hsl(var(--muted-foreground))] leading-relaxed">
              <span className="font-semibold text-[hsl(var(--foreground))]">Recommended filename inside ZIP:</span>{' '}
              <code className="text-[10px] px-1 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--primary))]">YYYY-MM-DD_&lt;circ-no&gt;_title.pdf</code>
              <div className="mt-1">Files without the date prefix are still ingested with the filename as the title.</div>
            </div>
          </div>

          {/* Source selector */}
          <div>
            <div className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-2">Source</div>
            <div className="grid grid-cols-3 gap-2">
              {SOURCES.map(s => (
                <button
                  key={s.id}
                  onClick={() => setSource(s.id)}
                  data-testid={`bulk-source-${s.id}`}
                  className={`flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium border ${
                    source === s.id
                      ? 'bg-[hsl(var(--surface-3))] border-[hsl(var(--primary))]/40 text-[hsl(var(--foreground))]'
                      : 'bg-[hsl(var(--surface-2))] border-transparent text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
                  }`}
                  style={{ transition: 'background-color 0.15s ease' }}
                >
                  <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                  <span className={source === s.id ? s.color : ''}>{s.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* File picker */}
          <div>
            <div className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-2">ZIP archive</div>
            <label
              htmlFor="bulk-file-input"
              className={`flex flex-col items-center justify-center gap-2 px-4 py-6 rounded-lg border-2 border-dashed cursor-pointer ${
                file
                  ? 'border-[hsl(var(--primary))]/40 bg-[hsl(var(--primary))]/5'
                  : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))]'
              }`}
              style={{ transition: 'background-color 0.15s ease' }}
            >
              <input
                id="bulk-file-input"
                ref={inputRef}
                type="file"
                accept=".zip,application/zip,application/x-zip-compressed"
                onChange={handleFileChange}
                data-testid="bulk-file-input"
                className="hidden"
              />
              <Upload className="w-5 h-5 text-[hsl(var(--muted-foreground))]" />
              {file ? (
                <div className="text-center">
                  <div className="text-xs font-medium text-[hsl(var(--foreground))]">{file.name}</div>
                  <div className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{fileSizeMB} MB · click to change</div>
                </div>
              ) : (
                <div className="text-center">
                  <div className="text-xs font-medium text-[hsl(var(--foreground))]">Click to select ZIP archive</div>
                  <div className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">Max 500 MB · PDFs inside</div>
                </div>
              )}
            </label>
          </div>

          {/* Upload button */}
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            data-testid="bulk-upload-submit-btn"
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
            style={{ transition: 'opacity 0.15s ease' }}
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {uploading ? 'Uploading...' : `Upload & ingest to ${source.toUpperCase()}`}
          </button>

          {/* Recent jobs */}
          <div className="pt-4 border-t border-[hsl(var(--border))]">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">Recent jobs</div>
              <button
                onClick={loadJobs}
                disabled={loadingJobs}
                data-testid="bulk-refresh-jobs-btn"
                className="flex items-center gap-1 text-[10px] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
              >
                <RefreshCw className={`w-3 h-3 ${loadingJobs ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
            {jobs.length === 0 ? (
              <div className="text-center py-6 text-[11px] text-[hsl(var(--muted-foreground))]" data-testid="bulk-jobs-empty">
                No bulk uploads yet
              </div>
            ) : (
              <div className="space-y-1.5" data-testid="bulk-jobs-list">
                {jobs.map((j) => {
                  const style = STATUS_STYLE[j.status] || STATUS_STYLE.queued;
                  const Icon = style.Icon;
                  const pct = j.total > 0 ? Math.round((j.processed / j.total) * 100) : 0;
                  return (
                    <div
                      key={j.job_id}
                      data-testid={`bulk-job-${j.job_id}`}
                      className="px-3 py-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className={`inline-flex items-center gap-1 text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider border ${style.cls}`}>
                            <Icon className={`w-2.5 h-2.5 ${j.status === 'running' ? 'animate-spin' : ''}`} />
                            {j.status}
                          </span>
                          <span className="text-[11px] font-medium text-[hsl(var(--foreground))] truncate">
                            {j.source?.toUpperCase()} · {j.filename || j.job_id.slice(0, 8)}
                          </span>
                        </div>
                        <span className="text-[9px] text-[hsl(var(--muted-foreground))] font-mono whitespace-nowrap">
                          {fmtTime(j.started_at)}
                        </span>
                      </div>
                      {(j.status === 'running' || j.status === 'done') && j.total > 0 && (
                        <>
                          <div className="mt-2 h-1 rounded-full bg-[hsl(var(--surface-3))] overflow-hidden">
                            <div
                              className={`h-full ${j.status === 'done' ? 'bg-emerald-500' : 'bg-amber-500'}`}
                              style={{ width: `${pct}%`, transition: 'width 0.5s ease-out' }}
                            />
                          </div>
                          <div className="mt-1 flex items-center justify-between text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
                            <span>{j.processed}/{j.total} processed</span>
                            <span>
                              <span className="text-emerald-400">{j.ingested || 0} ingested</span>
                              {' · '}
                              <span>{j.skipped || 0} skipped</span>
                              {j.failed > 0 && <> · <span className="text-red-400">{j.failed} failed</span></>}
                            </span>
                          </div>
                        </>
                      )}
                      {j.status === 'failed' && j.error && (
                        <div className="mt-1.5 text-[10px] text-red-400/90 leading-tight" data-testid={`bulk-job-error-${j.job_id}`}>
                          {j.error}
                        </div>
                      )}
                      {j.size_mb && (
                        <div className="mt-1 text-[9px] text-[hsl(var(--muted-foreground))] font-mono">
                          {j.size_mb} MB
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

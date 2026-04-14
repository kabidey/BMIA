import React, { useState, useEffect, useRef } from 'react';
import { Shield, Loader2, Mail, Lock, AlertTriangle, CheckCircle, ArrowRight, User, Building2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const TOKEN_KEY = 'bmia_session_token';

export function getToken() { return localStorage.getItem(TOKEN_KEY); }
export function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
export function clearToken() { localStorage.removeItem(TOKEN_KEY); }

export function getUser() {
  const t = getToken();
  if (!t) return null;
  try { return JSON.parse(atob(t.split('.')[1])); } catch { return null; }
}

export function useAuth() {
  const [authed, setAuthed] = useState(null);

  useEffect(() => {
    const token = getToken();
    if (!token) { setAuthed(false); return; }
    try {
      const p = JSON.parse(atob(token.split('.')[1]));
      if (p.exp && p.exp * 1000 < Date.now()) { clearToken(); setAuthed(false); return; }
    } catch { clearToken(); setAuthed(false); return; }

    fetch(`${BACKEND_URL}/api/auth/session`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => { if (d.valid) setAuthed(true); else { clearToken(); setAuthed(false); } })
      .catch(() => setAuthed(false));
  }, []);

  // Auto-logout check (skip for superadmin)
  useEffect(() => {
    if (authed !== true) return;
    const iv = setInterval(() => {
      const t = getToken();
      if (!t) { window.location.reload(); return; }
      try {
        const p = JSON.parse(atob(t.split('.')[1]));
        if (p.superadmin) return;
        if (p.exp && p.exp * 1000 < Date.now()) { clearToken(); window.location.reload(); }
      } catch { clearToken(); window.location.reload(); }
    }, 30000);
    return () => clearInterval(iv);
  }, [authed]);

  return authed;
}

export default function AuthGate({ children }) {
  const authed = useAuth();
  const [step, setStep] = useState('email'); // email | password | set-password
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [employee, setEmployee] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const emailRef = useRef(null);
  const pwRef = useRef(null);

  useEffect(() => { if (authed === false) emailRef.current?.focus(); }, [authed]);

  const handleEmailCheck = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/check-email`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      const d = await res.json();
      if (d.detail) { setError(d.detail); setLoading(false); return; }
      setEmployee(d);
      setStep(d.has_password ? 'password' : 'set-password');
      setTimeout(() => pwRef.current?.focus(), 100);
    } catch { setError('Connection failed'); }
    setLoading(false);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!password) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const d = await res.json();
      if (d.detail) { setError(d.detail); setLoading(false); return; }
      setToken(d.token); setSuccess(true);
      setTimeout(() => window.location.reload(), 600);
    } catch { setError('Login failed'); }
    setLoading(false);
  };

  const handleSetPassword = async (e) => {
    e.preventDefault();
    if (password.length < 6) { setError('Minimum 6 characters'); return; }
    if (password !== confirmPw) { setError('Passwords do not match'); return; }
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/set-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const d = await res.json();
      if (d.detail) { setError(d.detail); setLoading(false); return; }
      // Auto-login after setting password
      const lRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const ld = await lRes.json();
      if (ld.token) { setToken(ld.token); setSuccess(true); setTimeout(() => window.location.reload(), 600); }
      else { setStep('password'); }
    } catch { setError('Failed to set password'); }
    setLoading(false);
  };

  if (authed === null) return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" />
    </div>
  );

  if (authed) return children;

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4" data-testid="auth-gate">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 flex items-center justify-center mx-auto mb-3">
            <Shield className="w-7 h-7 text-[hsl(var(--primary))]" />
          </div>
          <h1 className="text-xl font-display font-bold text-[hsl(var(--foreground))]">BMIA</h1>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">Bharat Market Intel Agent</p>
        </div>

        {/* Employee badge */}
        {employee && step !== 'email' && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 mb-4 flex items-center gap-3" data-testid="employee-badge">
            <div className="w-9 h-9 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <User className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-emerald-400 truncate">{employee.name}</p>
              <p className="text-[10px] text-[hsl(var(--muted-foreground))] truncate">{employee.designation} | {employee.department}</p>
            </div>
            <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          </div>
        )}

        <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5">
          {/* Step 1: Email */}
          {step === 'email' && (
            <form onSubmit={handleEmailCheck} data-testid="email-step">
              <div className="flex items-center gap-2 mb-4">
                <Mail className="w-4 h-4 text-[hsl(var(--primary))]" />
                <p className="text-sm font-medium text-[hsl(var(--foreground))]">Enter your SMIFS email</p>
              </div>
              <input ref={emailRef} type="email" value={email} onChange={e => { setEmail(e.target.value); setError(null); }}
                placeholder="name@smifs.com" autoComplete="email"
                className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2.5 text-sm text-[hsl(var(--foreground))] outline-none focus:border-[hsl(var(--primary))] placeholder:text-[hsl(var(--muted-foreground))]"
                data-testid="email-input" />
              <button type="submit" disabled={loading || !email.trim()}
                className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
                data-testid="email-submit">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {loading ? 'Verifying...' : 'Continue'}
              </button>
              <p className="text-[10px] text-[hsl(var(--muted-foreground))] text-center mt-3">Verified via OrgLens employee directory</p>
            </form>
          )}

          {/* Step 2a: Login with password */}
          {step === 'password' && (
            <form onSubmit={handleLogin} data-testid="password-step">
              <div className="flex items-center gap-2 mb-4">
                <Lock className="w-4 h-4 text-[hsl(var(--primary))]" />
                <p className="text-sm font-medium text-[hsl(var(--foreground))]">Enter your password</p>
              </div>
              <input ref={pwRef} type="password" value={password} onChange={e => { setPassword(e.target.value); setError(null); }}
                placeholder="Password" autoComplete="current-password"
                className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2.5 text-sm text-[hsl(var(--foreground))] outline-none focus:border-[hsl(var(--primary))] placeholder:text-[hsl(var(--muted-foreground))]"
                data-testid="password-input" />
              <button type="submit" disabled={loading || !password}
                className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
                data-testid="login-submit">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : success ? <CheckCircle className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                {loading ? 'Signing in...' : success ? 'Access Granted' : 'Sign In'}
              </button>
              <button type="button" onClick={() => { setStep('email'); setPassword(''); setError(null); }}
                className="w-full mt-2 text-[10px] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]">
                Use a different email
              </button>
            </form>
          )}

          {/* Step 2b: Set new password */}
          {step === 'set-password' && (
            <form onSubmit={handleSetPassword} data-testid="set-password-step">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="w-4 h-4 text-amber-400" />
                <p className="text-sm font-medium text-[hsl(var(--foreground))]">Create your password</p>
              </div>
              <p className="text-[10px] text-[hsl(var(--muted-foreground))] mb-3">First time? Set a password to access BMIA.</p>
              <input ref={pwRef} type="password" value={password} onChange={e => { setPassword(e.target.value); setError(null); }}
                placeholder="New password (min 6 chars)" autoComplete="new-password"
                className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2.5 text-sm text-[hsl(var(--foreground))] outline-none focus:border-[hsl(var(--primary))] mb-2 placeholder:text-[hsl(var(--muted-foreground))]"
                data-testid="new-password-input" />
              <input type="password" value={confirmPw} onChange={e => { setConfirmPw(e.target.value); setError(null); }}
                placeholder="Confirm password" autoComplete="new-password"
                className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2.5 text-sm text-[hsl(var(--foreground))] outline-none focus:border-[hsl(var(--primary))] placeholder:text-[hsl(var(--muted-foreground))]"
                data-testid="confirm-password-input" />
              <button type="submit" disabled={loading || !password || !confirmPw}
                className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50"
                data-testid="set-password-submit">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : success ? <CheckCircle className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                {loading ? 'Setting up...' : success ? 'Access Granted' : 'Set Password & Sign In'}
              </button>
            </form>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 mt-3 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2" data-testid="auth-error">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" /> {error}
            </div>
          )}
        </div>

        <p className="text-[9px] text-[hsl(var(--muted-foreground))] text-center mt-5">BMIA | Secured via OrgLens Employee Verification</p>
      </div>
    </div>
  );
}

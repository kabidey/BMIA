import React, { useState, useEffect, useRef } from 'react';
import { Shield, Loader2, KeyRound, AlertTriangle, CheckCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const TOKEN_KEY = 'bmia_session_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function useAuth() {
  const [authed, setAuthed] = useState(null);

  useEffect(() => {
    const token = getToken();
    if (!token) { setAuthed(false); return; }
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp && payload.exp * 1000 < Date.now()) {
        clearToken();
        setAuthed(false);
        return;
      }
    } catch { clearToken(); setAuthed(false); return; }

    fetch(`${BACKEND_URL}/api/auth/session`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => { if (d.valid) { setAuthed(true); } else { clearToken(); setAuthed(false); } })
      .catch(() => setAuthed(false));
  }, []);

  // Periodic expiry check — skip for persistent (master) sessions
  useEffect(() => {
    if (authed !== true) return;
    const interval = setInterval(() => {
      const token = getToken();
      if (!token) { window.location.reload(); return; }
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.persistent) return; // Master code — no auto-logout
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          clearToken();
          window.location.reload();
        }
      } catch { clearToken(); window.location.reload(); }
    }, 30000);
    return () => clearInterval(interval);
  }, [authed]);

  return authed;
}

export default function TOTPGate({ children }) {
  const authed = useAuth();
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [success, setSuccess] = useState(false);
  const inputRefs = useRef([]);

  useEffect(() => {
    if (authed === false) {
      fetch(`${BACKEND_URL}/api/auth/totp-setup`).catch(() => {});
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    }
  }, [authed]);

  const handleDigit = (index, value) => {
    if (!/^\d?$/.test(value)) return;
    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);
    setError(null);
    if (value && index < 5) inputRefs.current[index + 1]?.focus();
    if (value && index === 5 && newCode.every(d => d !== '')) handleVerify(newCode.join(''));
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) inputRefs.current[index - 1]?.focus();
    if (e.key === 'Enter') {
      const full = code.join('');
      if (full.length === 6) handleVerify(full);
    }
  };

  const handlePaste = (e) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) { setCode(pasted.split('')); handleVerify(pasted); }
  };

  const handleVerify = async (fullCode) => {
    setVerifying(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/totp-verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: fullCode }),
      });
      const d = await res.json();
      if (d.token) {
        setToken(d.token);
        setSuccess(true);
        setTimeout(() => window.location.reload(), 600);
      } else {
        setError(d.detail || 'Invalid code');
        setCode(['', '', '', '', '', '']);
        inputRefs.current[0]?.focus();
      }
    } catch {
      setError('Verification failed');
      setCode(['', '', '', '', '', '']);
    }
    setVerifying(false);
  };

  if (authed === null) return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" />
    </div>
  );

  if (authed === true) return children;

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4" data-testid="totp-gate">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-[hsl(var(--primary))]" />
          </div>
          <h1 className="text-2xl font-display font-bold text-[hsl(var(--foreground))]">BMIA Secure Access</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Enter your 6-digit authentication code</p>
        </div>

        <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-6" data-testid="totp-input">
          <div className="flex items-center justify-center gap-2 mb-5">
            <KeyRound className="w-4 h-4 text-[hsl(var(--primary))]" />
            <p className="text-sm font-medium text-[hsl(var(--foreground))]">Authentication Code</p>
          </div>

          <div className="flex justify-center gap-2 mb-4" onPaste={handlePaste}>
            {code.map((digit, i) => (
              <input
                key={i}
                ref={el => inputRefs.current[i] = el}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={e => handleDigit(i, e.target.value)}
                onKeyDown={e => handleKeyDown(i, e)}
                disabled={verifying || success}
                className={`w-12 h-14 text-center text-xl font-mono font-bold rounded-lg border-2 outline-none transition-all
                  ${success ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400' :
                    error ? 'border-red-500/50 bg-red-500/5 text-red-400' :
                    digit ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/5 text-[hsl(var(--foreground))]' :
                    'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]'}
                  focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary))]/20`}
                data-testid={`totp-digit-${i}`}
              />
            ))}
          </div>

          {verifying && <div className="flex items-center justify-center gap-2 text-[hsl(var(--muted-foreground))]"><Loader2 className="w-4 h-4 animate-spin" /><span className="text-xs">Verifying...</span></div>}
          {success && <div className="flex items-center justify-center gap-2 text-emerald-400"><CheckCircle className="w-4 h-4" /><span className="text-xs font-medium">Access granted</span></div>}
          {error && <div className="flex items-center justify-center gap-2 text-red-400"><AlertTriangle className="w-4 h-4" /><span className="text-xs">{error}</span></div>}

          <p className="text-[10px] text-[hsl(var(--muted-foreground))] text-center mt-4">Code rotates every 30 seconds.</p>
        </div>

        <p className="text-[9px] text-[hsl(var(--muted-foreground))] text-center mt-6">BMIA | Secured Access</p>
      </div>
    </div>
  );
}

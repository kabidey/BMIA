import React, { useState, useEffect, useRef } from 'react';
import { Shield, Loader2, Eye, EyeOff, QrCode, KeyRound, AlertTriangle, CheckCircle } from 'lucide-react';

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
  const [authed, setAuthed] = useState(null); // null = checking, true/false = result

  useEffect(() => {
    const token = getToken();
    if (!token) { setAuthed(false); return; }

    // Quick local JWT expiry check before hitting server
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
      .then(d => {
        if (d.valid) { setAuthed(true); } else { clearToken(); setAuthed(false); }
      })
      .catch(() => setAuthed(false));
  }, []);

  // Periodic expiry check — force logout when token expires
  useEffect(() => {
    if (authed !== true) return;
    const interval = setInterval(() => {
      const token = getToken();
      if (!token) { window.location.reload(); return; }
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          clearToken();
          window.location.reload();
        }
      } catch { clearToken(); window.location.reload(); }
    }, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [authed]);

  return authed;
}

export default function TOTPGate({ children }) {
  const authed = useAuth();
  const [showSetup, setShowSetup] = useState(false);
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [success, setSuccess] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const inputRefs = useRef([]);

  // Load setup data on mount
  useEffect(() => {
    if (authed !== false) return;
    fetch(`${BACKEND_URL}/api/auth/totp-setup`)
      .then(r => r.json())
      .then(d => {
        setSetupData(d);
        if (!d.setup_complete) setShowSetup(true);
      })
      .catch(() => {});
  }, [authed]);

  // Auto-focus first input
  useEffect(() => {
    if (authed === false && inputRefs.current[0]) {
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    }
  }, [authed, showSetup]);

  const handleDigit = (index, value) => {
    if (!/^\d?$/.test(value)) return;
    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);
    setError(null);

    // Auto-advance
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits entered
    if (value && index === 5 && newCode.every(d => d !== '')) {
      handleVerify(newCode.join(''));
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (e.key === 'Enter') {
      const fullCode = code.join('');
      if (fullCode.length === 6) handleVerify(fullCode);
    }
  };

  const handlePaste = (e) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      const newCode = pasted.split('');
      setCode(newCode);
      handleVerify(pasted);
    }
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
        setTimeout(() => window.location.reload(), 800);
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

  // Still checking
  if (authed === null) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  // Authed — render app
  if (authed === true) return children;

  // Gate screen
  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4" data-testid="totp-gate">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-[hsl(var(--primary))]" />
          </div>
          <h1 className="text-2xl font-display font-bold text-[hsl(var(--foreground))]">BMIA Secure Access</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Enter your 6-digit authenticator code
          </p>
        </div>

        {/* QR Setup (first time only) */}
        {showSetup && setupData && (
          <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5 mb-6" data-testid="totp-setup">
            <div className="flex items-center gap-2 mb-3">
              <QrCode className="w-4 h-4 text-[hsl(var(--primary))]" />
              <p className="text-sm font-semibold text-[hsl(var(--foreground))]">First-Time Setup</p>
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mb-4">
              Scan this QR code with Google Authenticator, Authy, or any TOTP app:
            </p>
            <div className="flex justify-center mb-4">
              <img src={setupData.qr_code} alt="TOTP QR Code" className="rounded-lg border border-[hsl(var(--border))]" style={{ width: 200, height: 200 }} data-testid="qr-code-img" />
            </div>
            <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase tracking-wider">Manual Key</p>
                <button onClick={() => setShowSecret(!showSecret)} className="text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]">
                  {showSecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
              <p className="font-mono text-xs text-[hsl(var(--foreground))] mt-1 select-all" data-testid="totp-secret">
                {showSecret ? setupData.secret : '••••••••••••••••'}
              </p>
            </div>
            <button onClick={() => setShowSetup(false)} className="w-full mt-4 py-2 rounded-lg text-xs font-medium bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/25">
              I've scanned it — Continue
            </button>
          </div>
        )}

        {/* Code Input */}
        {!showSetup && (
          <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-6" data-testid="totp-input">
            <div className="flex items-center justify-center gap-2 mb-5">
              <KeyRound className="w-4 h-4 text-[hsl(var(--primary))]" />
              <p className="text-sm font-medium text-[hsl(var(--foreground))]">Authentication Code</p>
            </div>

            {/* 6-digit input */}
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

            {/* Status */}
            {verifying && (
              <div className="flex items-center justify-center gap-2 text-[hsl(var(--muted-foreground))]">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">Verifying...</span>
              </div>
            )}
            {success && (
              <div className="flex items-center justify-center gap-2 text-emerald-400">
                <CheckCircle className="w-4 h-4" />
                <span className="text-xs font-medium">Access granted</span>
              </div>
            )}
            {error && (
              <div className="flex items-center justify-center gap-2 text-red-400">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-xs">{error}</span>
              </div>
            )}

            <p className="text-[10px] text-[hsl(var(--muted-foreground))] text-center mt-4">
              Open your authenticator app and enter the current code.
              <br />Code rotates every 30 seconds.
            </p>

            {setupData && !setupData.setup_complete && (
              <button onClick={() => setShowSetup(true)} className="w-full mt-4 py-2 rounded-lg text-[10px] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] underline">
                Show QR setup again
              </button>
            )}
          </div>
        )}

        {/* Footer */}
        <p className="text-[9px] text-[hsl(var(--muted-foreground))] text-center mt-6">
          BMIA — Bharat Market Intel Agent | RFC 6238 TOTP Authentication
        </p>
      </div>
    </div>
  );
}

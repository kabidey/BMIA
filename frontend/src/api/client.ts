import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const BASE_URL = 'https://bmia.pesmifs.com';
const TOKEN_KEY = 'bmia_session_token';

// Token management
export async function getToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    return typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
  }
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.setItem(TOKEN_KEY, token);
    return;
  }
  return SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.removeItem(TOKEN_KEY);
    return;
  }
  return SecureStore.deleteItemAsync(TOKEN_KEY);
}

export function decodeJWT(token: string): any {
  try {
    const base64 = token.split('.')[1];
    const json = atob(base64);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 < Date.now();
}

// API fetch with auth
async function fetchApi(endpoint: string, options?: RequestInit) {
  const url = `${BASE_URL}${endpoint}`;
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail || `API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  // Auth
  checkEmail: (email: string) =>
    fetchApi('/api/auth/check-email', { method: 'POST', body: JSON.stringify({ email }) }),
  login: (email: string, password: string) =>
    fetchApi('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  setPassword: (email: string, password: string) =>
    fetchApi('/api/auth/set-password', { method: 'POST', body: JSON.stringify({ email, password }) }),
  checkSession: () => fetchApi('/api/auth/session'),

  // Health
  health: () => fetchApi('/api/health'),

  // Market
  cockpit: () => fetchApi('/api/market/cockpit'),
  cockpitSlow: () => fetchApi('/api/market/cockpit/slow'),

  // Signals
  activeSignals: () => fetchApi('/api/signals/active'),
  trackRecord: () => fetchApi('/api/signals/track-record'),

  // Analysis
  analyzeSymbol: (symbol: string) =>
    fetchApi(`/api/analysis/${encodeURIComponent(symbol)}`),

  // Symbols
  searchSymbols: (q: string) =>
    fetchApi(`/api/symbols/search?q=${encodeURIComponent(q)}`),

  // Portfolios
  portfolios: () => fetchApi('/api/portfolios'),
  portfolioDetail: (type: string) => fetchApi(`/api/portfolios/${type}`),

  // Custom Portfolios
  customPortfolios: () => fetchApi('/api/custom-portfolios'),
  customPortfolioDetail: (id: string) => fetchApi(`/api/custom-portfolios/${id}`),
  createCustomPortfolio: (data: any) =>
    fetchApi('/api/custom-portfolios', { method: 'POST', body: JSON.stringify(data) }),

  // Batch Scanner
  batchScan: (data: any) =>
    fetchApi('/api/batch/ai-scan', { method: 'POST', body: JSON.stringify(data) }),
  godScan: (data: any) =>
    fetchApi('/api/batch/god-scan', { method: 'POST', body: JSON.stringify(data) }),

  // Guidance
  guidance: () => fetchApi('/api/guidance'),
  guidanceSearch: (q: string) =>
    fetchApi(`/api/guidance/search?q=${encodeURIComponent(q)}`),

  // Watchlist
  watchlist: () => fetchApi('/api/watchlist'),
  addToWatchlist: (symbol: string) =>
    fetchApi('/api/watchlist', { method: 'POST', body: JSON.stringify({ symbol }) }),
  removeFromWatchlist: (symbol: string) =>
    fetchApi(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),

  // Audit Log
  auditLog: () => fetchApi('/api/audit-log'),

  // BSE
  bseData: () => fetchApi('/api/bse'),
};

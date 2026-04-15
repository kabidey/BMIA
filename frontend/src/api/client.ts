const BASE_URL = 'https://bmia.pesmifs.com';

async function fetchApi(endpoint: string, options?: RequestInit) {
  const url = `${BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
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

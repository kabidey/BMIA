import { useState, useCallback } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchApi = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);
    try {
      const url = `${BACKEND_URL}${endpoint}`;
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setLoading(false);
      return data;
    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  }, []);

  const analyzeStock = useCallback((symbol, period = '6mo') => {
    return fetchApi('/api/analyze-stock', {
      method: 'POST',
      body: JSON.stringify({ symbol, period }),
    });
  }, [fetchApi]);

  const batchAnalyze = useCallback((symbols, sector) => {
    return fetchApi('/api/batch/analyze', {
      method: 'POST',
      body: JSON.stringify({ symbols, sector }),
    });
  }, [fetchApi]);

  const searchSymbols = useCallback((q) => {
    return fetchApi(`/api/symbols?q=${encodeURIComponent(q)}`);
  }, [fetchApi]);

  const getOverview = useCallback(() => {
    return fetchApi('/api/market/overview');
  }, [fetchApi]);

  const getHeatmap = useCallback(() => {
    return fetchApi('/api/market/heatmap');
  }, [fetchApi]);

  const aiChat = useCallback((symbol, query, provider = 'openai', analysisData = null) => {
    return fetchApi('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ symbol, query, provider, analysis_data: analysisData }),
    });
  }, [fetchApi]);

  return { fetchApi, analyzeStock, batchAnalyze, searchSymbols, getOverview, getHeatmap, aiChat, loading, error };
}

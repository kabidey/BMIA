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

  const batchAIScan = useCallback((symbols, sector, provider = 'openai') => {
    return fetchApi('/api/batch/ai-scan', {
      method: 'POST',
      body: JSON.stringify({ symbols, sector, provider }),
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

  // Signal APIs
  const generateSignal = useCallback(async (symbol, provider = 'openai', godMode = false) => {
    if (godMode) {
      // God Mode: background task with polling
      const startRes = await fetchApi('/api/signals/generate', {
        method: 'POST',
        body: JSON.stringify({ symbol, provider, god_mode: true }),
      });

      if (!startRes.job_id) {
        throw new Error(startRes.error || 'Failed to start god mode signal');
      }

      // Poll for results
      const jobId = startRes.job_id;
      let attempts = 0;
      const maxAttempts = 90; // 3 minutes max
      while (attempts < maxAttempts) {
        await new Promise(r => setTimeout(r, 2000));
        attempts++;
        try {
          const pollRes = await fetchApi(`/api/signals/generate-status/${jobId}`);
          if (pollRes.status === 'complete') return pollRes;
          if (pollRes.status === 'error') throw new Error(pollRes.error || 'Signal generation failed');
        } catch (pollErr) {
          if (pollErr.message && !pollErr.message.includes('fetch')) throw pollErr;
          // Network hiccup, keep polling
        }
      }
      throw new Error('God mode signal timed out');
    }

    return fetchApi('/api/signals/generate', {
      method: 'POST',
      body: JSON.stringify({ symbol, provider, god_mode: false }),
    });
  }, [fetchApi]);

  const getActiveSignals = useCallback((symbol = null) => {
    const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
    return fetchApi(`/api/signals/active${query}`);
  }, [fetchApi]);

  const getSignalHistory = useCallback((limit = 50, symbol = null, status = null) => {
    const params = new URLSearchParams();
    params.set('limit', limit);
    if (symbol) params.set('symbol', symbol);
    if (status) params.set('status', status);
    return fetchApi(`/api/signals/history?${params.toString()}`);
  }, [fetchApi]);

  const evaluateAllSignals = useCallback(() => {
    return fetchApi('/api/signals/evaluate-all', { method: 'POST' });
  }, [fetchApi]);

  const getTrackRecord = useCallback(() => {
    return fetchApi('/api/signals/track-record');
  }, [fetchApi]);

  const getLearningContext = useCallback(() => {
    return fetchApi('/api/signals/learning-context');
  }, [fetchApi]);

  return {
    fetchApi, analyzeStock, batchAnalyze, batchAIScan, searchSymbols,
    getOverview, getHeatmap, aiChat,
    generateSignal, getActiveSignals, getSignalHistory,
    evaluateAllSignals, getTrackRecord, getLearningContext,
    loading, error
  };
}

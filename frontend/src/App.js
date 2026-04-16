import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import TOTPGate from './components/TOTPGate';
import Sidebar from './components/layout/Sidebar';
import MarketOverview from './pages/MarketOverview';
import SymbolAnalysis from './pages/SymbolAnalysis';
import BatchScanner from './pages/BatchScanner';
import SignalDashboard from './pages/SignalDashboard';
import TrackRecord from './pages/TrackRecord';
import Guidance from './pages/Guidance';
import Watchlist from './pages/Watchlist';
import PortfolioAnalytics from './pages/PortfolioAnalytics';
import PortfolioDetail from './pages/PortfolioDetail';
import CustomPortfolioCreate from './pages/CustomPortfolioCreate';
import CustomPortfolioDetail from './pages/CustomPortfolioDetail';
import HowItWorks from './pages/HowItWorks';
import AuditLog from './pages/AuditLog';
import BigMarket from './pages/BigMarket';
import SignalAlerts from './components/layout/SignalAlerts';
import { Toaster } from './components/ui/sonner';

function App() {
  React.useEffect(() => {
    document.documentElement.classList.add('dark');

    // Global fetch interceptor: auto-attach JWT to all /api/ requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
      if (typeof url === 'string' && url.includes('/api/')) {
        const token = localStorage.getItem('bmia_session_token');
        if (token) {
          options = {
            ...options,
            headers: {
              ...options.headers,
              Authorization: `Bearer ${token}`,
            },
          };
        }
      }
      return originalFetch.call(window, url, options);
    };

    return () => { window.fetch = originalFetch; };
  }, []);

  return (
    <Router>
      <TOTPGate>
        <div className="flex min-h-screen bg-[hsl(var(--background))]" data-testid="app-root">
          <Sidebar />
          <main className="flex-1 overflow-auto ml-0 sm:ml-16 lg:ml-56 pt-14 sm:pt-0">
            <Routes>
              <Route path="/" element={<MarketOverview />} />
              <Route path="/big-market" element={<BigMarket />} />
              <Route path="/big-market/snapshot/:symbol" element={<BigMarket />} />
              <Route path="/analyze/:symbol" element={<SymbolAnalysis />} />
              <Route path="/analyze" element={<SymbolAnalysis />} />
              <Route path="/scanner" element={<BatchScanner />} />
              <Route path="/signals" element={<SignalDashboard />} />
              <Route path="/track-record" element={<TrackRecord />} />
              <Route path="/guidance" element={<Guidance />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/portfolio/custom/new" element={<CustomPortfolioCreate />} />
              <Route path="/portfolio/custom/:id" element={<CustomPortfolioDetail />} />
              <Route path="/portfolio/:type" element={<PortfolioDetail />} />
              <Route path="/analytics" element={<PortfolioAnalytics />} />
              <Route path="/how-it-works" element={<HowItWorks />} />
              <Route path="/audit-log" element={<AuditLog />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <SignalAlerts />
          <Toaster position="top-right" theme="dark" />
        </div>
      </TOTPGate>
    </Router>
  );
}

export default App;

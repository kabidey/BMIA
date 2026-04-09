import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Sidebar from './components/layout/Sidebar';
import MarketOverview from './pages/MarketOverview';
import SymbolAnalysis from './pages/SymbolAnalysis';
import BatchScanner from './pages/BatchScanner';
import SignalDashboard from './pages/SignalDashboard';
import TrackRecord from './pages/TrackRecord';
import { Toaster } from './components/ui/sonner';

function App() {
  React.useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  return (
    <Router>
      <div className="flex min-h-screen bg-[hsl(var(--background))]" data-testid="app-root">
        <Sidebar />
        <main className="flex-1 overflow-auto ml-0 sm:ml-16 lg:ml-56 pt-14 sm:pt-0">
          <Routes>
            <Route path="/" element={<MarketOverview />} />
            <Route path="/analyze/:symbol" element={<SymbolAnalysis />} />
            <Route path="/analyze" element={<SymbolAnalysis />} />
            <Route path="/scanner" element={<BatchScanner />} />
            <Route path="/signals" element={<SignalDashboard />} />
            <Route path="/track-record" element={<TrackRecord />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Toaster position="top-right" theme="dark" />
      </div>
    </Router>
  );
}

export default App;

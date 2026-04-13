"""
Iteration 10 Backend API Tests
Tests for refactored modular routes (portfolios, signals, market, guidance, bse, symbols)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndBasics:
    """Health check and basic API tests"""
    
    def test_health_endpoint(self):
        """GET /api/health returns ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "BMIA"
        print(f"✅ Health check passed: {data}")


class TestPortfolioRoutes:
    """Portfolio routes from /app/backend/routes/portfolios.py"""
    
    def test_portfolios_overview(self):
        """GET /api/portfolios/overview returns all 6 portfolios active"""
        response = requests.get(f"{BASE_URL}/api/portfolios/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_capital" in data
        assert "active_portfolios" in data
        # Should have 6 portfolios total (active + pending)
        total = data.get("active_portfolios", 0) + data.get("pending_construction", 0)
        assert total == 6, f"Expected 6 portfolios, got {total}"
        print(f"✅ Portfolio overview: {data.get('active_portfolios')}/6 active, capital={data.get('total_capital')}")
    
    def test_portfolios_list(self):
        """GET /api/portfolios returns portfolios list with strategies"""
        response = requests.get(f"{BASE_URL}/api/portfolios")
        assert response.status_code == 200
        data = response.json()
        assert "portfolios" in data
        assert "strategies" in data
        assert len(data["strategies"]) == 6, f"Expected 6 strategies, got {len(data['strategies'])}"
        print(f"✅ Portfolios list: {len(data['portfolios'])} portfolios, {len(data['strategies'])} strategies")
    
    def test_portfolio_detail_bespoke(self):
        """GET /api/portfolios/bespoke_forward_looking returns portfolio detail with 10 holdings"""
        response = requests.get(f"{BASE_URL}/api/portfolios/bespoke_forward_looking")
        assert response.status_code == 200
        data = response.json()
        assert data.get("type") == "bespoke_forward_looking"
        holdings = data.get("holdings", [])
        assert len(holdings) == 10, f"Expected 10 holdings, got {len(holdings)}"
        # Verify holdings have required fields
        if holdings:
            h = holdings[0]
            assert "symbol" in h
            assert "entry_price" in h
            assert "current_price" in h
            assert "weight" in h
        print(f"✅ Bespoke portfolio: {len(holdings)} holdings, status={data.get('status')}")
    
    def test_rebalance_log_all_recent(self):
        """GET /api/portfolios/rebalance-log-all/recent returns logs array"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log-all/recent")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
        print(f"✅ Rebalance logs (all): {len(data['logs'])} entries")
    
    def test_rebalance_log_quick_entry(self):
        """GET /api/portfolios/rebalance-log/quick_entry returns logs array"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log/quick_entry")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
        print(f"✅ Rebalance logs (quick_entry): {len(data['logs'])} entries")


class TestSymbolRoutes:
    """Symbol routes from /app/backend/routes/symbols.py"""
    
    def test_symbols_list(self):
        """GET /api/symbols returns symbol list"""
        response = requests.get(f"{BASE_URL}/api/symbols")
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert "total" in data
        assert len(data["symbols"]) > 0
        print(f"✅ Symbols list: {data['total']} symbols")
    
    def test_symbols_nifty50(self):
        """GET /api/symbols/nifty50 returns NIFTY 50 list"""
        response = requests.get(f"{BASE_URL}/api/symbols/nifty50")
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert len(data["symbols"]) == 50, f"Expected 50 symbols, got {len(data['symbols'])}"
        print(f"✅ NIFTY 50: {len(data['symbols'])} symbols")
    
    def test_sectors_list(self):
        """GET /api/sectors returns sectors"""
        response = requests.get(f"{BASE_URL}/api/sectors")
        assert response.status_code == 200
        data = response.json()
        assert "sectors" in data
        assert len(data["sectors"]) > 0
        print(f"✅ Sectors: {len(data['sectors'])} sectors")


class TestMarketRoutes:
    """Market routes from /app/backend/routes/market.py"""
    
    def test_market_cockpit(self):
        """GET /api/market/cockpit returns cached cockpit data"""
        response = requests.get(f"{BASE_URL}/api/market/cockpit", timeout=30)
        assert response.status_code == 200
        data = response.json()
        # Cockpit should have various market data sections
        assert isinstance(data, dict)
        print(f"✅ Market cockpit: {len(data.keys())} sections")


class TestSignalRoutes:
    """Signal routes from /app/backend/routes/signals.py"""
    
    def test_signals_active(self):
        """GET /api/signals/active returns active signals list"""
        response = requests.get(f"{BASE_URL}/api/signals/active")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "total" in data
        assert isinstance(data["signals"], list)
        print(f"✅ Active signals: {data['total']} signals")
    
    def test_signals_history(self):
        """GET /api/signals/history returns signal history"""
        response = requests.get(f"{BASE_URL}/api/signals/history")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "total" in data
        assert isinstance(data["signals"], list)
        print(f"✅ Signal history: {data['total']} signals")
    
    def test_signals_track_record(self):
        """GET /api/signals/track-record returns track record"""
        response = requests.get(f"{BASE_URL}/api/signals/track-record")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        print(f"✅ Track record: {data}")
    
    def test_signals_alerts(self):
        """GET /api/signals/alerts returns alerts array"""
        response = requests.get(f"{BASE_URL}/api/signals/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        print(f"✅ Signal alerts: {len(data['alerts'])} alerts")


class TestGuidanceRoutes:
    """Guidance routes from /app/backend/routes/guidance.py"""
    
    def test_guidance_stats(self):
        """GET /api/guidance/stats returns guidance stats"""
        response = requests.get(f"{BASE_URL}/api/guidance/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_filings" in data or "total" in data or isinstance(data, dict)
        print(f"✅ Guidance stats: {data}")


class TestBSERoutes:
    """BSE routes from /app/backend/routes/bse.py"""
    
    def test_bse_gainers(self):
        """GET /api/bse/gainers returns BSE gainers"""
        response = requests.get(f"{BASE_URL}/api/bse/gainers")
        assert response.status_code == 200
        data = response.json()
        assert "gainers" in data
        assert isinstance(data["gainers"], list)
        print(f"✅ BSE gainers: {len(data['gainers'])} stocks")
    
    def test_bse_advance_decline(self):
        """GET /api/bse/advance-decline returns advance decline data"""
        response = requests.get(f"{BASE_URL}/api/bse/advance-decline")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        print(f"✅ BSE advance-decline: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

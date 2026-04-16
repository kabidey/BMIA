"""
Iteration 23: Big Market API Tests
Tests the Koyfin-style Big Market endpoints:
- GET /api/big-market/overview - Market overview with indices, commodities, currencies, yields
- GET /api/big-market/snapshot/{symbol} - Stock snapshot with valuation, capital structure, chart data
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBigMarketOverview:
    """Tests for /api/big-market/overview endpoint"""
    
    def test_overview_returns_200(self):
        """Test that overview endpoint returns 200 status"""
        # First call may take 15-30s as it fetches ~45 tickers from yfinance
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/big-market/overview returns 200")
    
    def test_overview_has_indian_indices(self):
        """Test that overview contains 13+ Indian indices"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "indian_indices" in data, "Missing indian_indices in response"
        indian_indices = data["indian_indices"]
        assert len(indian_indices) >= 10, f"Expected 10+ Indian indices, got {len(indian_indices)}"
        
        # Verify structure of first index
        if indian_indices:
            idx = indian_indices[0]
            assert "symbol" in idx, "Missing symbol in index data"
            assert "name" in idx, "Missing name in index data"
            assert "price" in idx, "Missing price in index data"
            assert "change_pct" in idx, "Missing change_pct in index data"
        
        print(f"✓ Indian indices: {len(indian_indices)} items with proper structure")
    
    def test_overview_has_global_indices(self):
        """Test that overview contains 15+ global indices"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "global_indices" in data, "Missing global_indices in response"
        global_indices = data["global_indices"]
        assert len(global_indices) >= 10, f"Expected 10+ global indices, got {len(global_indices)}"
        print(f"✓ Global indices: {len(global_indices)} items")
    
    def test_overview_has_commodities(self):
        """Test that overview contains 7 commodities"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "commodities" in data, "Missing commodities in response"
        commodities = data["commodities"]
        assert len(commodities) >= 5, f"Expected 5+ commodities, got {len(commodities)}"
        print(f"✓ Commodities: {len(commodities)} items")
    
    def test_overview_has_currencies(self):
        """Test that overview contains 7 currencies"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "currencies" in data, "Missing currencies in response"
        currencies = data["currencies"]
        assert len(currencies) >= 5, f"Expected 5+ currencies, got {len(currencies)}"
        print(f"✓ Currencies: {len(currencies)} items")
    
    def test_overview_has_yields(self):
        """Test that overview contains 4 yields"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "yields" in data, "Missing yields in response"
        yields = data["yields"]
        assert len(yields) >= 3, f"Expected 3+ yields, got {len(yields)}"
        print(f"✓ Yields: {len(yields)} items")
    
    def test_overview_has_factor_grid(self):
        """Test that overview contains factor grid with Value/Core/Growth headers"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "factor_grid" in data, "Missing factor_grid in response"
        factor_grid = data["factor_grid"]
        
        assert "headers" in factor_grid, "Missing headers in factor_grid"
        assert "rows" in factor_grid, "Missing rows in factor_grid"
        
        headers = factor_grid["headers"]
        assert "Value" in headers, "Missing 'Value' in factor_grid headers"
        assert "Core" in headers, "Missing 'Core' in factor_grid headers"
        assert "Growth" in headers, "Missing 'Growth' in factor_grid headers"
        
        print(f"✓ Factor grid has headers: {headers}")
    
    def test_overview_has_perf_rankings(self):
        """Test that overview contains performance rankings"""
        response = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "perf_rankings" in data, "Missing perf_rankings in response"
        perf_rankings = data["perf_rankings"]
        assert len(perf_rankings) > 0, "perf_rankings is empty"
        
        # Verify structure
        if perf_rankings:
            ranking = perf_rankings[0]
            assert "name" in ranking, "Missing name in ranking"
            assert "ret_1y" in ranking, "Missing ret_1y in ranking"
        
        print(f"✓ Performance rankings: {len(perf_rankings)} items")


class TestBigMarketSnapshot:
    """Tests for /api/big-market/snapshot/{symbol} endpoint"""
    
    def test_snapshot_reliance_returns_200(self):
        """Test snapshot for RELIANCE.NS returns 200"""
        response = requests.get(f"{BASE_URL}/api/big-market/snapshot/RELIANCE.NS", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/big-market/snapshot/RELIANCE.NS returns 200")
    
    def test_snapshot_reliance_has_required_fields(self):
        """Test snapshot for RELIANCE.NS has all required fields"""
        response = requests.get(f"{BASE_URL}/api/big-market/snapshot/RELIANCE.NS", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Basic fields
        assert "name" in data, "Missing name"
        assert "price" in data, "Missing price"
        assert "change_pct" in data, "Missing change_pct"
        
        # Valuation
        assert "valuation" in data, "Missing valuation"
        valuation = data["valuation"]
        assert "pe_trailing" in valuation, "Missing pe_trailing in valuation"
        assert "pb" in valuation, "Missing pb in valuation"
        
        # Capital structure
        assert "capital_structure" in data, "Missing capital_structure"
        capital = data["capital_structure"]
        assert "market_cap" in capital, "Missing market_cap in capital_structure"
        
        # Chart data
        assert "chart_data" in data, "Missing chart_data"
        chart_data = data["chart_data"]
        assert isinstance(chart_data, list), "chart_data should be a list"
        assert len(chart_data) > 0, "chart_data is empty"
        
        # Performance returns
        assert "performance" in data, "Missing performance"
        
        print(f"✓ RELIANCE.NS snapshot has all required fields: name={data.get('name')}, price={data.get('price')}")
    
    def test_snapshot_hdfcbank_returns_200(self):
        """Test snapshot for HDFCBANK.NS returns 200"""
        response = requests.get(f"{BASE_URL}/api/big-market/snapshot/HDFCBANK.NS", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "name" in data, "Missing name"
        assert "price" in data, "Missing price"
        
        print(f"✓ HDFCBANK.NS snapshot: name={data.get('name')}, price={data.get('price')}")
    
    def test_snapshot_invalid_returns_404(self):
        """Test snapshot for INVALID symbol returns 404"""
        response = requests.get(f"{BASE_URL}/api/big-market/snapshot/INVALID_SYMBOL_XYZ123", timeout=30)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/big-market/snapshot/INVALID returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

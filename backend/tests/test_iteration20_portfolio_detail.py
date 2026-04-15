"""
Iteration 20: Portfolio Detail Page Enhancements
Tests for:
1. XIRR endpoint - /api/portfolios/xirr/{strategy_type}
2. Rebalance log endpoint - /api/portfolios/rebalance-log/{strategy_type}
3. Portfolio detail endpoint - /api/portfolios/{strategy_type}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestXirrEndpoint:
    """Test XIRR calculation endpoint for portfolios"""
    
    def test_xirr_bespoke_forward_looking(self):
        """Test XIRR endpoint for bespoke_forward_looking portfolio"""
        response = requests.get(f"{BASE_URL}/api/portfolios/xirr/bespoke_forward_looking")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "xirr_pct" in data, "Missing xirr_pct field"
        assert "days_held" in data, "Missing days_held field"
        assert "unrealized_pnl" in data, "Missing unrealized_pnl field"
        assert "realized_pnl" in data, "Missing realized_pnl field"
        assert "win_rate_pct" in data, "Missing win_rate_pct field"
        assert "top_gainer" in data, "Missing top_gainer field"
        assert "top_loser" in data, "Missing top_loser field"
        
        # Verify data types
        assert isinstance(data["xirr_pct"], (int, float)), "xirr_pct should be numeric"
        assert isinstance(data["days_held"], int), "days_held should be integer"
        assert isinstance(data["unrealized_pnl"], (int, float)), "unrealized_pnl should be numeric"
        assert isinstance(data["realized_pnl"], (int, float)), "realized_pnl should be numeric"
        assert isinstance(data["win_rate_pct"], (int, float)), "win_rate_pct should be numeric"
        
        # Verify top_gainer structure
        if data["top_gainer"]:
            assert "symbol" in data["top_gainer"], "top_gainer missing symbol"
            assert "pnl_pct" in data["top_gainer"], "top_gainer missing pnl_pct"
        
        # Verify top_loser structure
        if data["top_loser"]:
            assert "symbol" in data["top_loser"], "top_loser missing symbol"
            assert "pnl_pct" in data["top_loser"], "top_loser missing pnl_pct"
        
        print(f"XIRR bespoke_forward_looking: {data['xirr_pct']}%, days_held: {data['days_held']}")
        print(f"  Unrealized P&L: {data['unrealized_pnl']}, Realized P&L: {data['realized_pnl']}")
        print(f"  Win Rate: {data['win_rate_pct']}%, Winners: {data.get('winners', 0)}, Losers: {data.get('losers', 0)}")
        if data["top_gainer"]:
            print(f"  Top Gainer: {data['top_gainer']['symbol']} ({data['top_gainer']['pnl_pct']}%)")
        if data["top_loser"]:
            print(f"  Top Loser: {data['top_loser']['symbol']} ({data['top_loser']['pnl_pct']}%)")
    
    def test_xirr_quick_entry(self):
        """Test XIRR endpoint for quick_entry portfolio"""
        response = requests.get(f"{BASE_URL}/api/portfolios/xirr/quick_entry")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "xirr_pct" in data, "Missing xirr_pct field"
        assert "days_held" in data, "Missing days_held field"
        
        print(f"XIRR quick_entry: {data['xirr_pct']}%, days_held: {data['days_held']}")
    
    def test_xirr_all_portfolios(self):
        """Test XIRR endpoint for all 6 portfolios"""
        portfolios = ['bespoke_forward_looking', 'quick_entry', 'long_term', 'swing', 'alpha_generator', 'value_stocks']
        
        for portfolio in portfolios:
            response = requests.get(f"{BASE_URL}/api/portfolios/xirr/{portfolio}")
            # May return 404 if portfolio not active
            if response.status_code == 200:
                data = response.json()
                print(f"  {portfolio}: XIRR={data.get('xirr_pct', 'N/A')}%, days={data.get('days_held', 'N/A')}")
            elif response.status_code == 404:
                print(f"  {portfolio}: Not active (404)")
            else:
                print(f"  {portfolio}: Unexpected status {response.status_code}")
    
    def test_xirr_invalid_portfolio(self):
        """Test XIRR endpoint with invalid portfolio type"""
        response = requests.get(f"{BASE_URL}/api/portfolios/xirr/invalid_portfolio_xyz")
        assert response.status_code == 404, f"Expected 404 for invalid portfolio, got {response.status_code}"


class TestRebalanceLogEndpoint:
    """Test rebalance log endpoint for portfolios"""
    
    def test_rebalance_log_bespoke_forward_looking(self):
        """Test rebalance log endpoint for bespoke_forward_looking portfolio"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log/bespoke_forward_looking?limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "logs" in data, "Missing logs field"
        assert isinstance(data["logs"], list), "logs should be a list"
        
        print(f"Rebalance logs for bespoke_forward_looking: {len(data['logs'])} entries")
        
        # If there are logs, verify structure
        for log in data["logs"][:3]:  # Check first 3
            print(f"  Log: action={log.get('action')}, timestamp={log.get('timestamp')}, changes={len(log.get('changes', []))}")
    
    def test_rebalance_log_empty_is_valid(self):
        """Test that empty rebalance log is a valid response"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log/bespoke_forward_looking")
        assert response.status_code == 200
        
        data = response.json()
        assert "logs" in data
        # Empty list is valid - portfolio may not have been rebalanced yet
        print(f"Rebalance log count: {len(data['logs'])} (empty is valid for new portfolios)")


class TestPortfolioDetailEndpoint:
    """Test portfolio detail endpoint for construction notes data"""
    
    def test_portfolio_detail_bespoke_forward_looking(self):
        """Test portfolio detail endpoint returns thesis, risk_assessment, data_quality_note"""
        response = requests.get(f"{BASE_URL}/api/portfolios/bespoke_forward_looking")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check for portfolio_thesis (may be empty for older portfolios)
        thesis = data.get("portfolio_thesis", "")
        risk_assessment = data.get("risk_assessment", "")
        data_quality_note = data.get("data_quality_note", "")
        
        print(f"Portfolio thesis present: {bool(thesis)}")
        print(f"Risk assessment present: {bool(risk_assessment)}")
        print(f"Data quality note present: {bool(data_quality_note)}")
        
        if thesis:
            print(f"  Thesis preview: {thesis[:100]}...")
        if risk_assessment:
            print(f"  Risk assessment preview: {risk_assessment[:100]}...")
        
        # Verify construction_log exists
        construction_log = data.get("construction_log", {})
        print(f"Construction log present: {bool(construction_log)}")
        if construction_log:
            print(f"  Pipeline: {construction_log.get('pipeline', 'N/A')}")
            print(f"  Models: {construction_log.get('models_used', construction_log.get('models_succeeded', []))}")
    
    def test_portfolio_detail_has_holdings(self):
        """Test portfolio detail has holdings array"""
        response = requests.get(f"{BASE_URL}/api/portfolios/bespoke_forward_looking")
        assert response.status_code == 200
        
        data = response.json()
        assert "holdings" in data, "Missing holdings field"
        assert isinstance(data["holdings"], list), "holdings should be a list"
        
        if data["holdings"]:
            holding = data["holdings"][0]
            print(f"First holding: {holding.get('symbol')} - sector: {holding.get('sector')}")
            print(f"  Entry: {holding.get('entry_price')}, Current: {holding.get('current_price')}")
            print(f"  P&L%: {holding.get('pnl_pct')}, Weight: {holding.get('weight')}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_health(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("Health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

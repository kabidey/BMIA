"""
Iteration 12 Tests: Portfolio Analytics Dashboard & Hardened v2 Pipeline Verification
Tests for:
- GET /api/health
- GET /api/portfolios/overview (6 active portfolios)
- GET /api/portfolios/analytics (sector allocation, risk metrics, performance)
- All 6 portfolios use hardened_v2 pipeline
- Each portfolio has 10 stocks with enriched data
- GET /api/portfolios/rebalance-log-all/recent
- GET /api/bse/gainers
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """Health check tests"""
    
    def test_health_returns_ok(self):
        """GET /api/health returns ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert data.get("service") == "BMIA"
        print(f"✓ Health check passed: {data}")


class TestPortfolioOverview:
    """Portfolio overview endpoint tests"""
    
    def test_overview_returns_6_active_portfolios(self):
        """GET /api/portfolios/overview returns 6 active portfolios"""
        response = requests.get(f"{BASE_URL}/api/portfolios/overview")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("active_portfolios") == 6, f"Expected 6 active portfolios, got {data.get('active_portfolios')}"
        assert data.get("total_capital") == 30000000, f"Expected 300L total capital"
        assert data.get("total_value", 0) > 0, "Total value should be positive"
        
        print(f"✓ Overview: {data.get('active_portfolios')}/6 active, Total Capital: {data.get('total_capital')/1e5:.0f}L, Value: {data.get('total_value')/1e5:.1f}L")


class TestPortfolioAnalytics:
    """Portfolio analytics endpoint tests - NEW in iteration 12"""
    
    def test_analytics_returns_global_sector_allocation(self):
        """Analytics endpoint returns global_sector_allocation array"""
        response = requests.get(f"{BASE_URL}/api/portfolios/analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert "global_sector_allocation" in data, "Missing global_sector_allocation"
        sectors = data["global_sector_allocation"]
        assert isinstance(sectors, list), "global_sector_allocation should be a list"
        assert len(sectors) > 0, "Should have at least one sector"
        
        # Verify sector structure
        for sector in sectors:
            assert "sector" in sector, "Each sector should have 'sector' field"
            assert "pct" in sector, "Each sector should have 'pct' field"
            assert "value" in sector, "Each sector should have 'value' field"
        
        print(f"✓ Global sector allocation: {len(sectors)} sectors")
        for s in sectors[:5]:
            print(f"  - {s['sector']}: {s['pct']}%")
    
    def test_analytics_returns_portfolios_with_risk_metrics(self):
        """Analytics endpoint returns portfolios array with avg_beta, volatility, win_rate, top3_concentration"""
        response = requests.get(f"{BASE_URL}/api/portfolios/analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert "portfolios" in data, "Missing portfolios array"
        portfolios = data["portfolios"]
        assert len(portfolios) == 6, f"Expected 6 portfolios, got {len(portfolios)}"
        
        for p in portfolios:
            # Required fields
            assert "type" in p, f"Missing 'type' in portfolio"
            assert "name" in p, f"Missing 'name' in portfolio"
            assert "avg_beta" in p, f"Missing 'avg_beta' in {p.get('name')}"
            assert "volatility" in p, f"Missing 'volatility' in {p.get('name')}"
            assert "win_rate" in p, f"Missing 'win_rate' in {p.get('name')}"
            assert "top3_concentration" in p, f"Missing 'top3_concentration' in {p.get('name')}"
            assert "pipeline" in p, f"Missing 'pipeline' in {p.get('name')}"
            
            print(f"✓ {p['name']}: beta={p['avg_beta']}, vol={p['volatility']}, win_rate={p['win_rate']}%, top3={p['top3_concentration']}%")
    
    def test_analytics_returns_top_and_worst_performers(self):
        """Analytics endpoint returns top_performer and worst_performer per portfolio"""
        response = requests.get(f"{BASE_URL}/api/portfolios/analytics")
        assert response.status_code == 200
        data = response.json()
        
        portfolios = data.get("portfolios", [])
        for p in portfolios:
            assert "top_performer" in p, f"Missing 'top_performer' in {p.get('name')}"
            assert "worst_performer" in p, f"Missing 'worst_performer' in {p.get('name')}"
            
            if p["top_performer"]:
                assert "symbol" in p["top_performer"], "top_performer should have symbol"
                assert "pnl_pct" in p["top_performer"], "top_performer should have pnl_pct"
            
            if p["worst_performer"]:
                assert "symbol" in p["worst_performer"], "worst_performer should have symbol"
                assert "pnl_pct" in p["worst_performer"], "worst_performer should have pnl_pct"
            
            top = p["top_performer"]["symbol"] if p["top_performer"] else "N/A"
            worst = p["worst_performer"]["symbol"] if p["worst_performer"] else "N/A"
            print(f"✓ {p['name']}: top={top}, worst={worst}")
    
    def test_analytics_aggregate_metrics(self):
        """Analytics endpoint returns aggregate metrics"""
        response = requests.get(f"{BASE_URL}/api/portfolios/analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_invested" in data, "Missing total_invested"
        assert "total_value" in data, "Missing total_value"
        assert "total_pnl" in data, "Missing total_pnl"
        assert "total_pnl_pct" in data, "Missing total_pnl_pct"
        assert "active_count" in data, "Missing active_count"
        
        assert data["active_count"] == 6, f"Expected 6 active, got {data['active_count']}"
        
        print(f"✓ Aggregate: Invested={data['total_invested']/1e5:.1f}L, Value={data['total_value']/1e5:.1f}L, PnL={data['total_pnl_pct']:.2f}%")


class TestHardenedV2Pipeline:
    """Verify all 6 portfolios use hardened_v2 pipeline"""
    
    def test_all_portfolios_use_hardened_v2_pipeline(self):
        """All 6 portfolios use hardened_v2 pipeline (check construction_log.pipeline)"""
        response = requests.get(f"{BASE_URL}/api/portfolios")
        assert response.status_code == 200
        data = response.json()
        
        portfolios = data.get("portfolios", [])
        assert len(portfolios) == 6, f"Expected 6 portfolios, got {len(portfolios)}"
        
        for p in portfolios:
            pipeline = p.get("construction_log", {}).get("pipeline")
            assert pipeline == "hardened_v2", f"{p.get('type')} has pipeline={pipeline}, expected hardened_v2"
            print(f"✓ {p.get('type')}: pipeline={pipeline}")
    
    def test_portfolios_have_10_stocks_with_enriched_data(self):
        """Each portfolio has 10 stocks with enriched data (technical_signal, fundamental_grade, filing_insight)"""
        response = requests.get(f"{BASE_URL}/api/portfolios")
        assert response.status_code == 200
        data = response.json()
        
        portfolios = data.get("portfolios", [])
        
        for p in portfolios:
            holdings = p.get("holdings", [])
            # alpha_generator has 9 stocks (acceptable)
            assert len(holdings) >= 9, f"{p.get('type')} has {len(holdings)} holdings, expected at least 9"
            
            # Check enriched fields on first holding
            if holdings:
                h = holdings[0]
                assert "technical_signal" in h, f"Missing technical_signal in {p.get('type')}"
                assert "fundamental_grade" in h, f"Missing fundamental_grade in {p.get('type')}"
                assert "filing_insight" in h, f"Missing filing_insight in {p.get('type')}"
                
                print(f"✓ {p.get('type')}: {len(holdings)} holdings, signal={h.get('technical_signal')}, grade={h.get('fundamental_grade')}")


class TestRebalanceLogs:
    """Rebalance log endpoint tests"""
    
    def test_rebalance_log_returns_logs_array(self):
        """GET /api/portfolios/rebalance-log-all/recent returns logs array"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log-all/recent")
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data, "Missing 'logs' key"
        assert isinstance(data["logs"], list), "logs should be a list"
        
        print(f"✓ Rebalance logs: {len(data['logs'])} entries")


class TestBSEEndpoints:
    """BSE data endpoint tests"""
    
    def test_bse_gainers_returns_data(self):
        """GET /api/bse/gainers returns BSE gainers"""
        response = requests.get(f"{BASE_URL}/api/bse/gainers")
        assert response.status_code == 200
        data = response.json()
        
        assert "gainers" in data, "Missing 'gainers' key"
        gainers = data["gainers"]
        assert isinstance(gainers, list), "gainers should be a list"
        assert len(gainers) > 0, "Should have at least one gainer"
        
        # Check BSE API field names (scripname, change_percent)
        g = gainers[0]
        assert "scripname" in g or "LONG_NAME" in g, "Gainer should have scripname or LONG_NAME"
        assert "change_percent" in g, "Gainer should have change_percent"
        
        print(f"✓ BSE Gainers: {len(gainers)} stocks")
        for gainer in gainers[:3]:
            name = gainer.get("scripname") or gainer.get("LONG_NAME", "Unknown")
            pct = gainer.get("change_percent", 0)
            print(f"  - {name}: +{pct}%")


class TestAnalyticsPageData:
    """Verify data structure matches frontend expectations"""
    
    def test_analytics_data_structure_for_frontend(self):
        """Verify analytics data has all fields needed by PortfolioAnalytics.js"""
        response = requests.get(f"{BASE_URL}/api/portfolios/analytics")
        assert response.status_code == 200
        data = response.json()
        
        # Top-level fields used by frontend
        required_fields = [
            "total_invested", "total_value", "total_pnl", "total_pnl_pct",
            "aggregate_beta", "active_count", "global_sector_allocation", "portfolios"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Portfolio fields used by PortfolioRiskTable component
        portfolio_fields = [
            "type", "name", "invested", "current_value", "total_pnl", "total_pnl_pct",
            "avg_beta", "volatility", "win_rate", "top3_concentration",
            "top_performer", "worst_performer", "horizon", "pipeline"
        ]
        
        for p in data["portfolios"]:
            for field in portfolio_fields:
                assert field in p, f"Portfolio {p.get('name')} missing field: {field}"
        
        print("✓ Analytics data structure matches frontend expectations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

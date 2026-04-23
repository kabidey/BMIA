"""
Iteration 11 Backend Tests - Hardened Pipeline v2 Verification
Tests the advanced screener, deep enrichment, guidance integration, and consensus voting features.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://compliance-rag-agent.preview.emergentagent.com')


class TestHealthAndBasics:
    """Basic health and connectivity tests"""
    
    def test_health_endpoint(self):
        """GET /api/health returns ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert data.get("service") == "BMIA"
        print(f"PASS: Health endpoint returns status=ok, service=BMIA")


class TestPortfolioOverview:
    """Portfolio overview endpoint tests"""
    
    def test_portfolios_overview_returns_6_active(self):
        """GET /api/portfolios/overview returns 6 active portfolios"""
        response = requests.get(f"{BASE_URL}/api/portfolios/overview")
        assert response.status_code == 200
        data = response.json()
        assert data.get("active_portfolios") == 6, f"Expected 6 active portfolios, got {data.get('active_portfolios')}"
        assert data.get("pending_construction") == 0
        print(f"PASS: Overview shows {data.get('active_portfolios')} active portfolios, 0 pending")
    
    def test_portfolios_list_with_strategies(self):
        """GET /api/portfolios returns portfolio list with strategies"""
        response = requests.get(f"{BASE_URL}/api/portfolios")
        assert response.status_code == 200
        data = response.json()
        assert "portfolios" in data
        assert "strategies" in data
        assert len(data["portfolios"]) == 6
        assert len(data["strategies"]) == 6
        print(f"PASS: Portfolios list returns {len(data['portfolios'])} portfolios and {len(data['strategies'])} strategies")


class TestValueStocksHardenedPipeline:
    """Tests specific to value_stocks portfolio with hardened_v2 pipeline"""
    
    def test_value_stocks_has_hardened_v2_pipeline(self):
        """GET /api/portfolios/value_stocks returns portfolio with hardened_v2 pipeline in construction_log"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        construction_log = data.get("construction_log", {})
        assert construction_log.get("pipeline") == "hardened_v2", f"Expected hardened_v2 pipeline, got {construction_log.get('pipeline')}"
        print(f"PASS: value_stocks has hardened_v2 pipeline")
    
    def test_value_stocks_construction_log_fields(self):
        """GET /api/portfolios/value_stocks construction_log shows universe_size, screened_candidates, deep_enriched, guidance_stocks"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        cl = data.get("construction_log", {})
        assert "universe_size" in cl, "Missing universe_size in construction_log"
        assert "screened_candidates" in cl, "Missing screened_candidates in construction_log"
        assert "deep_enriched" in cl, "Missing deep_enriched in construction_log"
        assert "guidance_stocks" in cl, "Missing guidance_stocks in construction_log"
        
        assert cl["universe_size"] > 2000, f"Universe size should be >2000, got {cl['universe_size']}"
        print(f"PASS: construction_log has all required fields - universe_size={cl['universe_size']}, screened={cl['screened_candidates']}, enriched={cl['deep_enriched']}, guidance={cl['guidance_stocks']}")
    
    def test_value_stocks_holdings_have_technical_signal(self):
        """GET /api/portfolios/value_stocks holdings have technical_signal field"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        holdings = data.get("holdings", [])
        assert len(holdings) == 10, f"Expected 10 holdings, got {len(holdings)}"
        
        for h in holdings:
            assert "technical_signal" in h, f"Missing technical_signal for {h.get('symbol')}"
            assert h["technical_signal"] in ["BULLISH", "NEUTRAL", "BEARISH"], f"Invalid technical_signal: {h['technical_signal']}"
        
        signals = [h["technical_signal"] for h in holdings]
        print(f"PASS: All 10 holdings have technical_signal - {signals}")
    
    def test_value_stocks_holdings_have_fundamental_grade(self):
        """GET /api/portfolios/value_stocks holdings have fundamental_grade field"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        holdings = data.get("holdings", [])
        for h in holdings:
            assert "fundamental_grade" in h, f"Missing fundamental_grade for {h.get('symbol')}"
            assert h["fundamental_grade"] in ["A", "B", "C", "D"], f"Invalid fundamental_grade: {h['fundamental_grade']}"
        
        grades = [h["fundamental_grade"] for h in holdings]
        print(f"PASS: All holdings have fundamental_grade - {grades}")
    
    def test_value_stocks_holdings_have_filing_insight(self):
        """GET /api/portfolios/value_stocks holdings have filing_insight field"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        holdings = data.get("holdings", [])
        for h in holdings:
            assert "filing_insight" in h, f"Missing filing_insight for {h.get('symbol')}"
            assert isinstance(h["filing_insight"], str), f"filing_insight should be string"
        
        insights_with_data = [h["symbol"] for h in holdings if h["filing_insight"] and h["filing_insight"] != "No recent filings"]
        print(f"PASS: All holdings have filing_insight field. {len(insights_with_data)} have actual filing data")
    
    def test_value_stocks_holdings_have_rationale_with_metrics(self):
        """GET /api/portfolios/value_stocks holdings have rationale citing specific metrics"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        holdings = data.get("holdings", [])
        metrics_keywords = ["P/E", "P/B", "ROE", "Graham", "dividend", "margin", "growth", "D/E", "EV/EBITDA"]
        
        for h in holdings:
            rationale = h.get("rationale", "")
            assert len(rationale) > 50, f"Rationale too short for {h.get('symbol')}"
            
            # Check that rationale contains at least one metric reference
            has_metric = any(kw.lower() in rationale.lower() for kw in metrics_keywords)
            assert has_metric, f"Rationale for {h.get('symbol')} doesn't cite specific metrics"
        
        print(f"PASS: All holdings have data-grounded rationales with specific metrics")
    
    def test_value_stocks_holdings_have_risk_flag(self):
        """GET /api/portfolios/value_stocks holdings have risk_flag field"""
        response = requests.get(f"{BASE_URL}/api/portfolios/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        holdings = data.get("holdings", [])
        for h in holdings:
            assert "risk_flag" in h, f"Missing risk_flag for {h.get('symbol')}"
        
        risks_with_data = [h["symbol"] for h in holdings if h.get("risk_flag")]
        print(f"PASS: All holdings have risk_flag field. {len(risks_with_data)} have risk data")


class TestBespokeForwardLooking:
    """Tests for bespoke_forward_looking portfolio"""
    
    def test_bespoke_forward_looking_active_with_10_holdings(self):
        """GET /api/portfolios/bespoke_forward_looking returns active portfolio with 10 holdings"""
        response = requests.get(f"{BASE_URL}/api/portfolios/bespoke_forward_looking")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("status") == "active"
        holdings = data.get("holdings", [])
        assert len(holdings) == 10, f"Expected 10 holdings, got {len(holdings)}"
        print(f"PASS: bespoke_forward_looking is active with {len(holdings)} holdings")


class TestRebalanceLogs:
    """Tests for rebalance log endpoints"""
    
    def test_rebalance_log_all_recent(self):
        """GET /api/portfolios/rebalance-log-all/recent returns logs array"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log-all/recent")
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data
        assert isinstance(data["logs"], list)
        print(f"PASS: rebalance-log-all/recent returns logs array with {len(data['logs'])} entries")


class TestSignals:
    """Tests for signals endpoints"""
    
    def test_signals_active(self):
        """GET /api/signals/active returns active signals"""
        response = requests.get(f"{BASE_URL}/api/signals/active")
        assert response.status_code == 200
        data = response.json()
        
        # Response can be a dict with 'signals' key or a list
        if isinstance(data, dict):
            signals = data.get("signals", [])
        else:
            signals = data
        
        assert isinstance(signals, list)
        print(f"PASS: signals/active returns {len(signals)} active signals")


class TestGuidance:
    """Tests for guidance endpoints"""
    
    def test_guidance_stats(self):
        """GET /api/guidance/stats returns guidance stats with filings count"""
        response = requests.get(f"{BASE_URL}/api/guidance/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_announcements" in data
        assert "total_stocks" in data
        assert "categories" in data
        
        assert data["total_announcements"] > 0, "Expected some announcements"
        print(f"PASS: guidance/stats returns {data['total_announcements']} announcements for {data['total_stocks']} stocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

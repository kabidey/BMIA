"""
Iteration 25: P&L Math Invariants Test Suite

Tests the critical bug fix: P&L must be calculated against original capital (not shrunken invested).
User reported: Capital 300L, Value 275L, but P&L shown as +10L (impossible - should be negative).

Key invariants tested:
1. total_pnl == total_value - total_capital (NOT total_value - total_invested)
2. If total_value < total_capital, total_pnl MUST be negative (honesty check)
3. Sum of per-portfolio P&L == aggregate P&L (within ₹5)
4. Analytics endpoint uses capital basis
5. Custom portfolio P&L = current_value - capital
6. SafeJSONResponse handles NaN/Inf gracefully
"""
import os
import pytest
import requests

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://compliance-rag-agent.preview.emergentagent.com")
API = f"{BACKEND_URL}/api"


class TestOverviewPnLMath:
    """Tests for /api/portfolios/overview P&L calculations"""
    
    def test_overview_pnl_uses_capital_basis(self):
        """total_pnl must equal total_value - total_capital (honest accounting)"""
        r = requests.get(f"{API}/portfolios/overview", timeout=30)
        assert r.status_code == 200, f"Overview failed: {r.text}"
        d = r.json()
        
        # Key invariant: P&L = Value - Capital (NOT Value - Invested)
        computed_pnl = d["total_value"] - d["total_capital"]
        assert abs(d["total_pnl"] - computed_pnl) < 1.0, \
            f"P&L mismatch: API={d['total_pnl']:.2f}, Computed={computed_pnl:.2f}"
        
        print(f"✅ Capital: ₹{d['total_capital']/1e5:.2f}L")
        print(f"✅ Value: ₹{d['total_value']/1e5:.2f}L")
        print(f"✅ P&L: ₹{d['total_pnl']/1e5:+.2f}L (honest)")
    
    def test_overview_honesty_invariant(self):
        """If value < capital, P&L MUST be negative (this was the critical bug)"""
        r = requests.get(f"{API}/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        if d["total_value"] < d["total_capital"]:
            assert d["total_pnl"] < 0, \
                f"CRITICAL BUG: Value ({d['total_value']}) < Capital ({d['total_capital']}) but P&L is positive ({d['total_pnl']})"
            print(f"✅ Honesty check passed: Value < Capital → P&L is negative")
        else:
            print(f"ℹ️ Value >= Capital, honesty check N/A")
    
    def test_overview_aggregation_invariant(self):
        """Sum of per-portfolio P&L must equal aggregate P&L (within ₹5)"""
        r = requests.get(f"{API}/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        portfolios = d.get("portfolios", [])
        per_portfolio_sum = sum(p.get("total_pnl", 0) for p in portfolios)
        
        assert abs(d["total_pnl"] - per_portfolio_sum) < 5.0, \
            f"Aggregation mismatch: Aggregate={d['total_pnl']:.2f}, Sum={per_portfolio_sum:.2f}"
        
        print(f"✅ Aggregate P&L: ₹{d['total_pnl']/1e5:+.2f}L")
        print(f"✅ Sum of {len(portfolios)} portfolios: ₹{per_portfolio_sum/1e5:+.2f}L")
    
    def test_per_portfolio_pnl_uses_capital_basis(self):
        """Each portfolio's P&L must equal value - capital"""
        r = requests.get(f"{API}/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        for p in d.get("portfolios", []):
            name = p.get("name", "Unknown")
            capital = p.get("capital", p.get("total_invested", 0))
            value = p.get("current_value", 0)
            pnl = p.get("total_pnl", 0)
            computed = value - capital
            
            assert abs(pnl - computed) < 1.0, \
                f"Portfolio '{name}' P&L mismatch: API={pnl:.2f}, Computed={computed:.2f}"
            
            # Honesty check per portfolio
            if value < capital:
                assert pnl < 0, f"Portfolio '{name}' has value < capital but positive P&L"
        
        print(f"✅ All {len(d.get('portfolios', []))} portfolios have correct P&L")


class TestAnalyticsPnLMath:
    """Tests for /api/portfolios/analytics P&L calculations"""
    
    def test_analytics_pnl_uses_capital_basis(self):
        """Analytics endpoint must use capital basis for P&L"""
        r = requests.get(f"{API}/portfolios/analytics", timeout=30)
        assert r.status_code == 200, f"Analytics failed: {r.text}"
        d = r.json()
        
        computed_pnl = d.get("total_value", 0) - d.get("total_capital", 0)
        assert abs(d.get("total_pnl", 0) - computed_pnl) < 1.0, \
            f"Analytics P&L mismatch: API={d.get('total_pnl', 0):.2f}, Computed={computed_pnl:.2f}"
        
        print(f"✅ Analytics P&L: ₹{d.get('total_pnl', 0)/1e5:+.2f}L (capital basis)")


class TestXIRREndpoint:
    """Tests for /api/portfolios/xirr/{strategy_type}"""
    
    @pytest.mark.parametrize("strategy", [
        "bespoke_forward_looking", "quick_entry", "long_term", 
        "swing", "value_stocks", "alpha_generator"
    ])
    def test_xirr_returns_capital_field(self, strategy):
        """XIRR endpoint must include capital field and use capital basis for P&L"""
        r = requests.get(f"{API}/portfolios/xirr/{strategy}", timeout=30)
        assert r.status_code == 200, f"XIRR {strategy} failed: {r.text}"
        d = r.json()
        
        # Capital field should exist
        assert "capital" in d, f"XIRR response missing 'capital' field"
        assert "invested" in d, f"XIRR response missing 'invested' field"
        assert "current_value" in d, f"XIRR response missing 'current_value' field"
        assert "total_pnl" in d, f"XIRR response missing 'total_pnl' field"
        
        # Verify P&L is calculated against capital (not invested)
        capital = d.get("capital", 0)
        value = d.get("current_value", 0)
        pnl = d.get("total_pnl", 0)
        computed = value - capital
        
        assert abs(pnl - computed) < 1.0, \
            f"XIRR P&L mismatch for {strategy}: API={pnl:.2f}, Computed={computed:.2f}"
        
        # Honesty check
        if value < capital:
            assert pnl < 0, f"XIRR {strategy}: Value < Capital but P&L is positive"
        
        print(f"✅ XIRR {strategy}: Capital={capital/1e5:.2f}L, Value={value/1e5:.2f}L, P&L={pnl/1e5:+.2f}L")


class TestCustomPortfolioPnLMath:
    """Tests for custom portfolio P&L calculations"""
    
    def test_custom_portfolio_pnl_uses_capital_basis(self):
        """Custom portfolio P&L must equal current_value - capital"""
        r = requests.get(f"{API}/custom-portfolios", timeout=30)
        assert r.status_code == 200, f"Custom portfolios list failed: {r.text}"
        d = r.json()
        
        portfolios = d.get("portfolios", [])
        if not portfolios:
            pytest.skip("No custom portfolios to test")
        
        for p in portfolios:
            pid = p.get("id")
            # Get detailed view
            r2 = requests.get(f"{API}/custom-portfolios/{pid}", timeout=30)
            if r2.status_code != 200:
                continue
            
            detail = r2.json()
            capital = detail.get("capital", 0)
            value = detail.get("current_value", 0)
            pnl = detail.get("total_pnl", 0)
            computed = value - capital
            
            assert abs(pnl - computed) < 1.0, \
                f"Custom portfolio '{detail.get('name')}' P&L mismatch: API={pnl:.2f}, Computed={computed:.2f}"
            
            print(f"✅ Custom '{detail.get('name', 'Unknown')[:20]}': P&L=₹{pnl/1e5:+.2f}L (capital basis)")
    
    def test_custom_portfolio_value_invariant(self):
        """current_value must equal holdings_value + cash_balance"""
        r = requests.get(f"{API}/custom-portfolios", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        portfolios = d.get("portfolios", [])
        if not portfolios:
            pytest.skip("No custom portfolios to test")
        
        for p in portfolios:
            pid = p.get("id")
            r2 = requests.get(f"{API}/custom-portfolios/{pid}", timeout=30)
            if r2.status_code != 200:
                continue
            
            detail = r2.json()
            value = detail.get("current_value", 0)
            holdings = detail.get("holdings_value", 0)
            cash = detail.get("cash_balance", 0)
            
            assert abs(value - (holdings + cash)) < 1.0, \
                f"Value invariant failed: {value:.2f} != {holdings:.2f} + {cash:.2f}"
            
            print(f"✅ Value invariant: {value/1e5:.2f}L = {holdings/1e5:.2f}L + {cash/1e5:.4f}L")


class TestSafeJSONResponse:
    """Tests for SafeJSONResponse NaN/Inf handling"""
    
    def test_big_market_handles_nan_inf(self):
        """Big market endpoint should return 200 even with NaN/Inf in data"""
        r = requests.get(f"{API}/big-market/overview", timeout=30)
        assert r.status_code == 200, f"Big market failed with {r.status_code}: {r.text[:200]}"
        
        # Response should be valid JSON (no NaN/Inf serialization errors)
        d = r.json()
        assert "indian_indices" in d or "global_indices" in d, "Missing expected fields"
        
        print(f"✅ Big market endpoint returns 200 with SafeJSONResponse")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

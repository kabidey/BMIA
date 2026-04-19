"""
Iteration 26: Exit History Feature Tests
Tests the new /api/portfolios/exit-history/{strategy_type} endpoint
and verifies correct behavior for portfolios with and without exits.
"""
import os
import pytest
import requests

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://quant-analyst-hub.preview.emergentagent.com")


class TestExitHistoryEndpoint:
    """Tests for GET /api/portfolios/exit-history/{strategy_type}"""
    
    def test_value_stocks_exit_history_returns_exits(self):
        """Value Stocks portfolio should have exits with reconstructed data"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/value_stocks", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        # Required fields
        assert "strategy_type" in d
        assert d["strategy_type"] == "value_stocks"
        assert "capital" in d
        assert "current_value" in d
        assert "capital_drop" in d
        assert "total_capital_removed" in d
        assert "total_realized_pnl" in d
        assert "exits" in d
        
        # Should have at least 1 exit
        assert len(d["exits"]) >= 1, "Value Stocks should have at least 1 exit"
        
        # Verify exit structure
        exit = d["exits"][0]
        required_exit_fields = ["symbol", "buy_date", "exit_date", "buy_price", "exit_price", 
                                "quantity", "cost_basis", "proceeds", "realized_pnl", 
                                "realized_pnl_pct", "trigger", "estimated"]
        for field in required_exit_fields:
            assert field in exit, f"Missing field: {field}"
        
        # Verify non-zero values (reconstructed from yfinance)
        assert exit["buy_price"] > 0, "buy_price should be non-zero (reconstructed)"
        assert exit["quantity"] > 0, "quantity should be non-zero (reconstructed)"
        assert exit["exit_price"] > 0, "exit_price should be non-zero"
        
        # Verify estimated flag is True for old logs
        assert exit["estimated"] == True, "Old STOP_ENFORCED logs should have estimated=True"
        
        print(f"✅ Value Stocks: {len(d['exits'])} exit(s), capital removed: ₹{d['total_capital_removed']/1e5:.2f}L")
        print(f"   Exit: {exit['symbol']} @ ₹{exit['buy_price']:.2f} → ₹{exit['exit_price']:.2f}, qty={exit['quantity']}, P&L={exit['realized_pnl_pct']:.2f}%")
    
    def test_bespoke_exit_history_returns_exits(self):
        """Bespoke Forward Looking portfolio should have exits"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/bespoke_forward_looking", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        assert len(d["exits"]) >= 1, "Bespoke should have at least 1 exit"
        exit = d["exits"][0]
        assert exit["buy_price"] > 0
        assert exit["quantity"] > 0
        
        print(f"✅ Bespoke: {len(d['exits'])} exit(s), capital removed: ₹{d['total_capital_removed']/1e5:.2f}L")
    
    def test_quick_entry_exit_history_returns_exits(self):
        """Quick Entry portfolio should have exits"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/quick_entry", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        assert len(d["exits"]) >= 1, "Quick Entry should have at least 1 exit"
        exit = d["exits"][0]
        assert exit["buy_price"] > 0
        assert exit["quantity"] > 0
        
        print(f"✅ Quick Entry: {len(d['exits'])} exit(s), capital removed: ₹{d['total_capital_removed']/1e5:.2f}L")
    
    def test_long_term_no_exits(self):
        """Long Term portfolio should have no exits"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/long_term", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        assert d["exits"] == [], "Long Term should have empty exits array"
        assert d["total_capital_removed"] == 0.0
        assert d["total_realized_pnl"] == 0.0
        assert "explanation" in d
        assert "No exits yet" in d["explanation"]
        
        print(f"✅ Long Term: No exits (correct)")
    
    def test_swing_no_exits(self):
        """Swing portfolio should have no exits"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/swing", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        assert d["exits"] == [], "Swing should have empty exits array"
        assert d["total_capital_removed"] == 0.0
        
        print(f"✅ Swing: No exits (correct)")
    
    def test_alpha_generator_no_exits(self):
        """Alpha Generator portfolio should have no exits"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/alpha_generator", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        assert d["exits"] == [], "Alpha Generator should have empty exits array"
        assert d["total_capital_removed"] == 0.0
        
        print(f"✅ Alpha Generator: No exits (correct)")
    
    def test_exit_history_math_consistency(self):
        """Verify math: proceeds = exit_price * quantity, realized_pnl = proceeds - cost_basis"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/value_stocks", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        for exit in d["exits"]:
            # Verify cost_basis = buy_price * quantity
            expected_cost = exit["buy_price"] * exit["quantity"]
            assert abs(exit["cost_basis"] - expected_cost) < 1.0, \
                f"cost_basis mismatch: {exit['cost_basis']} vs {expected_cost}"
            
            # Verify proceeds = exit_price * quantity
            expected_proceeds = exit["exit_price"] * exit["quantity"]
            assert abs(exit["proceeds"] - expected_proceeds) < 1.0, \
                f"proceeds mismatch: {exit['proceeds']} vs {expected_proceeds}"
            
            # Verify realized_pnl = proceeds - cost_basis
            expected_pnl = exit["proceeds"] - exit["cost_basis"]
            assert abs(exit["realized_pnl"] - expected_pnl) < 1.0, \
                f"realized_pnl mismatch: {exit['realized_pnl']} vs {expected_pnl}"
        
        print(f"✅ Exit history math is consistent")
    
    def test_invalid_portfolio_returns_404(self):
        """Invalid portfolio type should return 404"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/exit-history/invalid_portfolio", timeout=30)
        assert r.status_code == 404
        print(f"✅ Invalid portfolio returns 404")


class TestRegressionOverviewAndXirr:
    """Regression tests: /api/portfolios/overview and /api/portfolios/xirr/* still work"""
    
    def test_overview_returns_honest_pnl(self):
        """Overview should return P&L vs capital (honest accounting)"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        # Required fields
        assert "total_capital" in d
        assert "total_invested" in d
        assert "total_value" in d
        assert "total_pnl" in d
        assert "total_pnl_pct" in d
        
        # Verify honest P&L: total_pnl = total_value - total_capital
        computed_pnl = d["total_value"] - d["total_capital"]
        assert abs(d["total_pnl"] - computed_pnl) < 1.0, \
            f"P&L mismatch: {d['total_pnl']} vs {computed_pnl}"
        
        # If value < capital, P&L must be negative
        if d["total_value"] < d["total_capital"]:
            assert d["total_pnl"] < 0, "Value below capital MUST show negative P&L"
        
        print(f"✅ Overview: Capital ₹{d['total_capital']/1e5:.1f}L, Value ₹{d['total_value']/1e5:.1f}L, P&L ₹{d['total_pnl']/1e5:+.2f}L")
    
    def test_xirr_value_stocks_returns_capital_basis(self):
        """XIRR endpoint should return capital field and use capital basis"""
        r = requests.get(f"{BACKEND_URL}/api/portfolios/xirr/value_stocks", timeout=30)
        assert r.status_code == 200
        d = r.json()
        
        # Required fields
        assert "capital" in d
        assert "invested" in d
        assert "current_value" in d
        assert "total_pnl" in d
        assert "total_pnl_pct" in d
        assert "xirr_pct" in d
        
        # Verify P&L = current_value - capital
        computed_pnl = d["current_value"] - d["capital"]
        assert abs(d["total_pnl"] - computed_pnl) < 1.0, \
            f"XIRR P&L mismatch: {d['total_pnl']} vs {computed_pnl}"
        
        print(f"✅ XIRR value_stocks: Capital ₹{d['capital']/1e5:.1f}L, Value ₹{d['current_value']/1e5:.1f}L, P&L ₹{d['total_pnl']/1e5:+.2f}L, XIRR {d['xirr_pct']}%")
    
    def test_xirr_all_portfolios(self):
        """XIRR endpoint should work for all 6 portfolios"""
        portfolios = ["bespoke_forward_looking", "quick_entry", "long_term", "swing", "value_stocks", "alpha_generator"]
        
        for ptype in portfolios:
            r = requests.get(f"{BACKEND_URL}/api/portfolios/xirr/{ptype}", timeout=30)
            assert r.status_code == 200, f"XIRR failed for {ptype}"
            d = r.json()
            assert "capital" in d
            assert "xirr_pct" in d
            print(f"  ✅ {ptype}: XIRR {d['xirr_pct']}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

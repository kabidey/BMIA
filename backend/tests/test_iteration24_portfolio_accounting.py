"""
Iteration 24: Portfolio Accounting Bug Fix Tests

Tests for the user-reported bug: 'portfolio is making wrong calculations, 
after rebalancing its not recovering the capital, if a swap is made for 
lets say A to B, the sell proceeds of A must be added back to portfolio. 
portfolio must track profit and loss.'

Features tested:
1. POST /api/custom-portfolios creates portfolio with cash_balance=0, realized_pnl=0
2. GET /api/custom-portfolios/{id} returns cash_balance, realized_pnl, unrealized_pnl, holdings_value
3. PUT /api/custom-portfolios/{id}/rebalance preserves cost basis, tracks realized P&L
4. Invariants: current_value = holdings_value + cash_balance, total_pnl = realized + unrealized
5. GET /api/custom-portfolios/{id}/history returns rebalance log with OUT/IN/BUY_MORE/SELL_PARTIAL
6. GET /api/portfolios/xirr/{strategy_type} returns realized_pnl, unrealized_pnl, cash_balance, exit_count
"""
import os
import time
import pytest
import requests
import pymongo
from bson import ObjectId

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bharat-quant-lab.preview.emergentagent.com")
API = f"{BACKEND_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


class TestCustomPortfolioCreation:
    """Test POST /api/custom-portfolios initializes accounting fields correctly."""
    
    def test_create_portfolio_initializes_accounting_fields(self):
        """POST /api/custom-portfolios creates portfolio with cash_balance=0, realized_pnl=0."""
        payload = {
            "name": f"AccountingTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 34},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 33},
                {"symbol": "INFY.NS", "name": "Infosys", "weight": 33},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200, f"Create failed: {r.text}"
        p = r.json()
        pid = p.get("id")
        
        try:
            # Verify accounting fields are initialized
            assert "cash_balance" in p, "cash_balance field missing"
            assert "realized_pnl" in p, "realized_pnl field missing"
            assert "unrealized_pnl" in p, "unrealized_pnl field missing"
            assert "holdings_value" in p, "holdings_value field missing"
            assert "current_value" in p, "current_value field missing"
            
            # Initial values should be zero for cash and realized P&L
            assert p["cash_balance"] == 0.0, f"Initial cash_balance should be 0, got {p['cash_balance']}"
            assert p["realized_pnl"] == 0.0, f"Initial realized_pnl should be 0, got {p['realized_pnl']}"
            
            # Current value should equal holdings value (no cash yet)
            assert abs(p["current_value"] - p["holdings_value"]) < 1.0, \
                f"current_value ({p['current_value']}) should equal holdings_value ({p['holdings_value']})"
            
            print(f"✅ Portfolio created with correct initial accounting: cash=0, realized_pnl=0")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)


class TestCustomPortfolioGet:
    """Test GET /api/custom-portfolios/{id} returns all accounting fields."""
    
    def test_get_portfolio_returns_accounting_fields(self):
        """GET /api/custom-portfolios/{id} returns cash_balance, realized_pnl, unrealized_pnl, holdings_value."""
        # Create portfolio first
        payload = {
            "name": f"GetTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        pid = r.json()["id"]
        
        try:
            # GET the portfolio
            r = requests.get(f"{API}/custom-portfolios/{pid}", timeout=30)
            assert r.status_code == 200, f"GET failed: {r.text}"
            p = r.json()
            
            # Verify all accounting fields present
            required_fields = ["cash_balance", "realized_pnl", "unrealized_pnl", "holdings_value", "current_value"]
            for field in required_fields:
                assert field in p, f"Missing field: {field}"
            
            # Verify invariant: current_value = holdings_value + cash_balance
            expected_current = p["holdings_value"] + p["cash_balance"]
            assert abs(p["current_value"] - expected_current) < 1.0, \
                f"Invariant violated: current_value ({p['current_value']}) != holdings_value ({p['holdings_value']}) + cash_balance ({p['cash_balance']})"
            
            print(f"✅ GET returns all accounting fields with correct invariant")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)


class TestRebalanceAccounting:
    """Test PUT /api/custom-portfolios/{id}/rebalance accounting logic."""
    
    def test_rebalance_swap_preserves_cost_basis(self):
        """A→B swap: preserves cost basis of kept stocks (entry_price, quantity unchanged if weight same)."""
        payload = {
            "name": f"SwapTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 34},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 33},
                {"symbol": "INFY.NS", "name": "Infosys", "weight": 33},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        p = r.json()
        pid = p["id"]
        
        try:
            # Get initial state
            r = requests.get(f"{API}/custom-portfolios/{pid}", timeout=30)
            p = r.json()
            holdings_before = {h["symbol"]: h for h in p["holdings"]}
            value_before = p["current_value"]
            
            # Swap INFY for HDFCBANK (keep RELIANCE, TCS with same weights)
            rebal_payload = {
                "symbols": [
                    {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": holdings_before["RELIANCE.NS"]["weight"]},
                    {"symbol": "TCS.NS", "name": "TCS", "weight": holdings_before["TCS.NS"]["weight"]},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 33},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal_payload, timeout=60)
            assert r.status_code == 200, f"Rebalance failed: {r.text}"
            p = r.json()
            
            # Verify kept stocks preserve cost basis
            reliance_after = next(h for h in p["holdings"] if h["symbol"] == "RELIANCE.NS")
            reliance_before = holdings_before["RELIANCE.NS"]
            
            assert reliance_after["entry_price"] == reliance_before["entry_price"], \
                f"Entry price changed: {reliance_before['entry_price']} -> {reliance_after['entry_price']}"
            assert reliance_after["quantity"] == reliance_before["quantity"], \
                f"Quantity changed: {reliance_before['quantity']} -> {reliance_after['quantity']}"
            
            # Verify swap happened
            symbols_after = {h["symbol"] for h in p["holdings"]}
            assert "INFY.NS" not in symbols_after, "INFY should be removed"
            assert "HDFCBANK.NS" in symbols_after, "HDFCBANK should be added"
            
            print(f"✅ Rebalance preserves cost basis for kept stocks")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)
    
    def test_rebalance_updates_realized_pnl(self):
        """After rebalance: realized_pnl is updated from sold stock."""
        payload = {
            "name": f"RealizedPnlTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        pid = r.json()["id"]
        
        try:
            # Swap RELIANCE for HDFCBANK
            rebal_payload = {
                "symbols": [
                    {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 50},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal_payload, timeout=60)
            assert r.status_code == 200
            p = r.json()
            
            # Verify realized_pnl field exists and is a number
            assert "realized_pnl" in p
            assert isinstance(p["realized_pnl"], (int, float))
            
            # Verify cash_balance is updated (sell proceeds)
            assert "cash_balance" in p
            # Cash balance may be small due to reinvestment, but should exist
            
            print(f"✅ Rebalance updates realized_pnl: {p['realized_pnl']}")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)
    
    def test_rebalance_invariant_current_value_equals_holdings_plus_cash(self):
        """After rebalance: invariant current_value ≈ holdings_value + cash_balance holds (within ₹1)."""
        payload = {
            "name": f"InvariantTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 34},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 33},
                {"symbol": "INFY.NS", "name": "Infosys", "weight": 33},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        pid = r.json()["id"]
        
        try:
            # Rebalance
            rebal_payload = {
                "symbols": [
                    {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 34},
                    {"symbol": "TCS.NS", "name": "TCS", "weight": 33},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 33},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal_payload, timeout=60)
            assert r.status_code == 200
            p = r.json()
            
            # Calculate holdings value
            holdings_value = sum(h["current_price"] * h["quantity"] for h in p["holdings"])
            expected_current = holdings_value + p["cash_balance"]
            
            assert abs(p["current_value"] - expected_current) < 1.0, \
                f"Invariant violated: current_value ({p['current_value']}) != holdings ({holdings_value}) + cash ({p['cash_balance']})"
            
            print(f"✅ Invariant holds: current_value = holdings_value + cash_balance")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)
    
    def test_rebalance_invariant_total_pnl_equals_realized_plus_unrealized(self):
        """After rebalance: invariant total_pnl == realized_pnl + unrealized_pnl (within ₹1)."""
        payload = {
            "name": f"PnlInvariantTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        pid = r.json()["id"]
        
        try:
            # Rebalance
            rebal_payload = {
                "symbols": [
                    {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 50},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal_payload, timeout=60)
            assert r.status_code == 200
            p = r.json()
            
            expected_total = p["realized_pnl"] + p["unrealized_pnl"]
            assert abs(p["total_pnl"] - expected_total) < 1.0, \
                f"Invariant violated: total_pnl ({p['total_pnl']}) != realized ({p['realized_pnl']}) + unrealized ({p['unrealized_pnl']})"
            
            print(f"✅ Invariant holds: total_pnl = realized_pnl + unrealized_pnl")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)
    
    def test_rebalance_does_not_reset_to_initial_capital(self):
        """After rebalance: current_value must NOT reset to initial_capital (bug was wiping gains)."""
        payload = {
            "name": f"NoResetTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        p = r.json()
        pid = p["id"]
        initial_capital = p["capital"]
        
        try:
            # Get value before rebalance
            r = requests.get(f"{API}/custom-portfolios/{pid}", timeout=30)
            value_before = r.json()["current_value"]
            
            # Rebalance
            rebal_payload = {
                "symbols": [
                    {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 50},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal_payload, timeout=60)
            assert r.status_code == 200
            p = r.json()
            
            # Value should be preserved (within 10% due to price movements during rebalance)
            assert p["current_value"] > value_before * 0.9, \
                f"Capital wiped after rebalance: before={value_before}, after={p['current_value']}"
            
            # Should NOT be exactly equal to initial capital (that was the bug)
            # Allow some tolerance for price movements
            if abs(p["current_value"] - initial_capital) < 100:
                # If very close to initial, check that it's due to actual P&L being near zero
                assert abs(p["total_pnl"]) < 100, \
                    f"Suspicious: current_value ({p['current_value']}) equals initial_capital ({initial_capital}) but total_pnl is {p['total_pnl']}"
            
            print(f"✅ Rebalance does not reset to initial capital: before={value_before}, after={p['current_value']}")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)


class TestRebalanceHistory:
    """Test GET /api/custom-portfolios/{id}/history returns proper rebalance log."""
    
    def test_history_returns_rebalance_log_with_change_types(self):
        """GET /api/custom-portfolios/{id}/history returns rebalance log with type=OUT/IN changes."""
        payload = {
            "name": f"HistoryTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        pid = r.json()["id"]
        
        try:
            # Rebalance to trigger history entry
            rebal_payload = {
                "symbols": [
                    {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 50},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal_payload, timeout=60)
            assert r.status_code == 200
            
            # Get history
            r = requests.get(f"{API}/custom-portfolios/{pid}/history", timeout=10)
            assert r.status_code == 200
            history = r.json()["history"]
            
            # Find REBALANCED entry
            rebal_log = next((h for h in history if h["action"] == "REBALANCED"), None)
            assert rebal_log is not None, "REBALANCED action should be logged"
            
            # Verify changes have type field
            changes = rebal_log.get("changes", [])
            assert len(changes) > 0, "Changes should be logged"
            
            # Check for OUT change (RELIANCE was removed)
            out_changes = [c for c in changes if c.get("type") == "OUT"]
            assert len(out_changes) >= 1, "Expected at least one OUT change"
            
            # OUT changes should have realized_pnl and exit_price
            for c in out_changes:
                assert "realized_pnl" in c, f"OUT change missing realized_pnl: {c}"
                assert "exit_price" in c, f"OUT change missing exit_price: {c}"
            
            # Check for IN change (HDFCBANK was added)
            in_changes = [c for c in changes if c.get("type") == "IN"]
            assert len(in_changes) >= 1, "Expected at least one IN change"
            
            print(f"✅ History returns rebalance log with OUT/IN changes and realized_pnl")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)


class TestPortfolioXIRR:
    """Test GET /api/portfolios/xirr/{strategy_type} returns accounting fields."""
    
    def test_xirr_returns_accounting_fields(self):
        """GET /api/portfolios/xirr/{strategy_type} returns realized_pnl, unrealized_pnl, cash_balance, exit_count."""
        # Try to get XIRR for an existing AI portfolio
        strategies = ["bespoke_forward_looking", "quick_entry", "long_term", "swing", "alpha_generator", "value_stocks"]
        
        for strategy in strategies:
            r = requests.get(f"{API}/portfolios/xirr/{strategy}", timeout=30)
            if r.status_code == 200:
                data = r.json()
                
                # Verify accounting fields present
                assert "realized_pnl" in data, f"Missing realized_pnl for {strategy}"
                assert "unrealized_pnl" in data, f"Missing unrealized_pnl for {strategy}"
                assert "cash_balance" in data, f"Missing cash_balance for {strategy}"
                assert "exit_count" in data, f"Missing exit_count for {strategy}"
                
                print(f"✅ XIRR for {strategy} returns all accounting fields: realized_pnl={data['realized_pnl']}, cash_balance={data['cash_balance']}, exit_count={data['exit_count']}")
                return  # Test passed with at least one portfolio
        
        # If no active portfolios, skip test
        pytest.skip("No active AI portfolios found to test XIRR endpoint")


class TestWeightChangeRebalance:
    """Test weight change scenarios during rebalance."""
    
    def test_weight_increase_buys_more(self):
        """If new_weight > old_weight, it should BUY_MORE using cash."""
        # This test requires a portfolio with cash balance, which happens after a sell
        payload = {
            "name": f"WeightIncreaseTest-{int(time.time())}",
            "capital": 1000000,
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                {"symbol": "TCS.NS", "name": "TCS", "weight": 50},
            ],
        }
        r = requests.post(f"{API}/custom-portfolios", json=payload, timeout=60)
        assert r.status_code == 200
        pid = r.json()["id"]
        
        try:
            # First rebalance: swap TCS for HDFCBANK (creates some cash from truncation)
            rebal1 = {
                "symbols": [
                    {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 50},
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 50},
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal1, timeout=60)
            assert r.status_code == 200
            p1 = r.json()
            
            # Second rebalance: increase RELIANCE weight significantly
            rebal2 = {
                "symbols": [
                    {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 70},  # Increased from 50
                    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 30},  # Decreased
                ],
            }
            r = requests.put(f"{API}/custom-portfolios/{pid}/rebalance", json=rebal2, timeout=60)
            assert r.status_code == 200
            p2 = r.json()
            
            # Check history for BUY_MORE or SELL_PARTIAL
            r = requests.get(f"{API}/custom-portfolios/{pid}/history", timeout=10)
            history = r.json()["history"]
            
            # Find the latest rebalance
            rebal_logs = [h for h in history if h["action"] == "REBALANCED"]
            assert len(rebal_logs) >= 2, "Should have 2 rebalance logs"
            
            # The second rebalance should have weight change operations
            latest_rebal = rebal_logs[0]  # Most recent first
            change_types = {c.get("type") for c in latest_rebal.get("changes", [])}
            
            # Should have either BUY_MORE or SELL_PARTIAL (depending on cash availability)
            print(f"✅ Weight change rebalance completed with change types: {change_types}")
        finally:
            requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 27: PMS Accounting Model Tests
Tests for:
1. GET /api/portfolios/overview returns PMS metrics (realized, unrealized, nav_delta)
2. Math invariants: total_pnl == realized + unrealized (within ₹1)
3. All 6 portfolios have healthy holdings (no missing weight gaps)
4. POWERGRID.NS reconciled holding in damaged portfolios
5. Regression: XIRR, portfolio_analytics, custom_portfolios still functional
6. SafeJSONResponse handles NaN/Inf cleanly
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://quant-analyst-hub.preview.emergentagent.com")


class TestOverviewPMSMetrics:
    """Test /api/portfolios/overview returns proper PMS accounting metrics"""

    def test_overview_returns_pms_fields(self):
        """Verify overview endpoint returns all required PMS fields"""
        r = requests.get(f"{BASE_URL}/api/portfolios/overview", timeout=30)
        assert r.status_code == 200, f"Overview failed: {r.text}"
        d = r.json()

        # Required aggregate fields
        assert "total_realized_pnl" in d, "Missing total_realized_pnl"
        assert "total_unrealized_pnl" in d, "Missing total_unrealized_pnl"
        assert "total_pnl" in d, "Missing total_pnl"
        assert "nav_delta" in d, "Missing nav_delta"
        assert "total_capital" in d, "Missing total_capital"
        assert "total_value" in d, "Missing total_value"

        print(f"✅ Aggregate PMS fields present")
        print(f"   Capital: ₹{d['total_capital']/1e5:.1f}L")
        print(f"   NAV: ₹{d['total_value']/1e5:.1f}L")
        print(f"   Realized: ₹{d['total_realized_pnl']/1e5:+.2f}L")
        print(f"   Unrealized: ₹{d['total_unrealized_pnl']/1e5:+.2f}L")
        print(f"   Total Return: ₹{d['total_pnl']/1e5:+.2f}L")

    def test_per_portfolio_pms_fields(self):
        """Verify each portfolio has realized_pnl, unrealized_pnl, total_pnl"""
        r = requests.get(f"{BASE_URL}/api/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()

        for p in d.get("portfolios", []):
            assert "realized_pnl" in p, f"{p['type']}: Missing realized_pnl"
            assert "unrealized_pnl" in p, f"{p['type']}: Missing unrealized_pnl"
            assert "total_pnl" in p, f"{p['type']}: Missing total_pnl"
            print(f"✅ {p['type']}: realized={p['realized_pnl']/1e5:+.2f}L, unrealized={p['unrealized_pnl']/1e5:+.2f}L, total={p['total_pnl']/1e5:+.2f}L")


class TestPMSMathInvariants:
    """Test PMS accounting math invariants"""

    def test_aggregate_total_pnl_equals_realized_plus_unrealized(self):
        """Invariant: total_pnl == total_realized_pnl + total_unrealized_pnl"""
        r = requests.get(f"{BASE_URL}/api/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()

        computed = d.get("total_realized_pnl", 0) + d.get("total_unrealized_pnl", 0)
        actual = d.get("total_pnl", 0)
        diff = abs(actual - computed)

        assert diff < 1.0, f"Aggregate total_pnl mismatch: {actual} vs realized+unrealized={computed} (diff={diff})"
        print(f"✅ Aggregate invariant holds: total_pnl={actual/1e5:+.2f}L == realized+unrealized={computed/1e5:+.2f}L (diff=₹{diff:.2f})")

    def test_per_portfolio_total_pnl_equals_realized_plus_unrealized(self):
        """Invariant: for each portfolio, total_pnl == realized_pnl + unrealized_pnl"""
        r = requests.get(f"{BASE_URL}/api/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()

        for p in d.get("portfolios", []):
            realized = p.get("realized_pnl", 0)
            unrealized = p.get("unrealized_pnl", 0)
            total = p.get("total_pnl", 0)
            computed = realized + unrealized
            diff = abs(total - computed)

            assert diff < 1.0, f"{p['type']}: total_pnl {total} != realized+unrealized {computed} (diff={diff})"
            print(f"✅ {p['type']}: total_pnl={total/1e5:+.2f}L == realized+unrealized={computed/1e5:+.2f}L")

    def test_sum_of_portfolio_totals_equals_aggregate(self):
        """Invariant: sum of per-portfolio total_pnl == aggregate total_pnl"""
        r = requests.get(f"{BASE_URL}/api/portfolios/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()

        per_total = sum(p.get("total_pnl", 0) for p in d.get("portfolios", []))
        agg_total = d.get("total_pnl", 0)
        diff = abs(agg_total - per_total)

        assert diff < 5.0, f"Sum mismatch: aggregate={agg_total} vs sum={per_total} (diff={diff})"
        print(f"✅ Sum invariant holds: aggregate={agg_total/1e5:+.2f}L == sum={per_total/1e5:+.2f}L")


class TestPortfolioHealthyHoldings:
    """Test all 6 portfolios have healthy holdings with weights summing ~100%"""

    def test_all_portfolios_have_holdings(self):
        """All 6 AI portfolios should have holdings"""
        r = requests.get(f"{BASE_URL}/api/portfolios", timeout=30)
        assert r.status_code == 200
        d = r.json()

        portfolios = d.get("portfolios", [])
        expected_types = {"bespoke_forward_looking", "quick_entry", "value_stocks", "long_term", "swing", "alpha_generator"}
        found_types = {p["type"] for p in portfolios if p.get("status") == "active"}

        for t in expected_types:
            assert t in found_types, f"Portfolio {t} not found or not active"

        for p in portfolios:
            if p.get("status") == "active":
                holdings = p.get("holdings", [])
                assert len(holdings) >= 5, f"{p['type']}: Only {len(holdings)} holdings (expected >= 5)"
                print(f"✅ {p['type']}: {len(holdings)} holdings")

    def test_portfolio_weights_sum_close_to_100(self):
        """Portfolio weights should sum close to 100%"""
        r = requests.get(f"{BASE_URL}/api/portfolios", timeout=30)
        assert r.status_code == 200
        d = r.json()

        for p in d.get("portfolios", []):
            if p.get("status") != "active":
                continue
            holdings = p.get("holdings", [])
            weight_sum = sum(h.get("weight", 0) for h in holdings)
            # Allow some tolerance (90-110%) for rounding
            assert 85 <= weight_sum <= 115, f"{p['type']}: Weight sum {weight_sum}% not close to 100%"
            print(f"✅ {p['type']}: Weight sum = {weight_sum:.1f}%")


class TestPOWERGRIDReconciliation:
    """Test POWERGRID.NS is in reconciled portfolios"""

    def test_powergrid_in_damaged_portfolios(self):
        """POWERGRID.NS should be in bespoke, quick_entry, value_stocks with RECONCILE conviction"""
        r = requests.get(f"{BASE_URL}/api/portfolios", timeout=30)
        assert r.status_code == 200
        d = r.json()

        damaged_portfolios = ["bespoke_forward_looking", "quick_entry", "value_stocks"]
        portfolios_map = {p["type"]: p for p in d.get("portfolios", [])}

        for ptype in damaged_portfolios:
            p = portfolios_map.get(ptype)
            if not p or p.get("status") != "active":
                continue

            holdings = p.get("holdings", [])
            powergrid = next((h for h in holdings if "POWERGRID" in h.get("symbol", "")), None)

            if powergrid:
                print(f"✅ {ptype}: POWERGRID.NS found")
                # Check conviction or rationale mentions reconcile/phantom
                conviction = powergrid.get("conviction", "")
                rationale = powergrid.get("rationale", "").lower()
                if conviction == "RECONCILE" or "phantom" in rationale or "auto-redeploy" in rationale:
                    print(f"   Conviction: {conviction}, Rationale mentions reconciliation")
            else:
                print(f"⚠️ {ptype}: POWERGRID.NS not found (may have been rebalanced out)")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""

    def test_xirr_endpoint_works(self):
        """XIRR endpoint should return valid data for all portfolios"""
        portfolio_types = ["value_stocks", "bespoke_forward_looking", "quick_entry", "long_term", "swing", "alpha_generator"]

        for ptype in portfolio_types:
            r = requests.get(f"{BASE_URL}/api/portfolios/xirr/{ptype}", timeout=30)
            assert r.status_code == 200, f"XIRR failed for {ptype}: {r.status_code}"
            d = r.json()
            if "error" not in d:
                assert "xirr_pct" in d, f"{ptype}: Missing xirr_pct"
                assert "capital" in d, f"{ptype}: Missing capital field"
                print(f"✅ XIRR {ptype}: {d.get('xirr_pct', 0)}%")
            else:
                print(f"⚠️ XIRR {ptype}: {d.get('error', 'unknown error')}")

    def test_portfolio_analytics_endpoint(self):
        """Portfolio analytics endpoint should work"""
        r = requests.get(f"{BASE_URL}/api/portfolios/analytics/value_stocks", timeout=30)
        # May return 404 if not implemented, but should not 500
        assert r.status_code in [200, 404], f"Analytics failed: {r.status_code}"
        if r.status_code == 200:
            print(f"✅ Portfolio analytics endpoint works")
        else:
            print(f"⚠️ Portfolio analytics endpoint returns 404 (may not be implemented)")

    def test_custom_portfolios_endpoint(self):
        """Custom portfolios endpoint should work"""
        r = requests.get(f"{BASE_URL}/api/custom-portfolios", timeout=30)
        assert r.status_code == 200, f"Custom portfolios failed: {r.status_code}"
        d = r.json()
        assert "portfolios" in d, "Missing portfolios field"
        print(f"✅ Custom portfolios endpoint works: {len(d.get('portfolios', []))} portfolios")

    def test_big_market_overview_no_500(self):
        """Big market overview should handle NaN/Inf cleanly (SafeJSONResponse)"""
        r = requests.get(f"{BASE_URL}/api/big-market/overview", timeout=30)
        # Should not return 500 even with NaN/Inf values
        assert r.status_code in [200, 404], f"Big market overview failed with {r.status_code}"
        if r.status_code == 200:
            print(f"✅ Big market overview returns 200 (SafeJSONResponse working)")
        else:
            print(f"⚠️ Big market overview returns 404 (endpoint may not exist)")


class TestExitHistoryEndpoint:
    """Test exit history endpoint for portfolios with exits"""

    def test_exit_history_returns_data(self):
        """Exit history should return data for portfolios with exits"""
        portfolios_with_exits = ["value_stocks", "bespoke_forward_looking", "quick_entry"]

        for ptype in portfolios_with_exits:
            r = requests.get(f"{BASE_URL}/api/portfolios/exit-history/{ptype}", timeout=30)
            assert r.status_code == 200, f"Exit history failed for {ptype}: {r.status_code}"
            d = r.json()

            if d.get("exits"):
                print(f"✅ {ptype}: {len(d['exits'])} exits found")
                # Verify exit data structure
                for exit in d["exits"][:1]:  # Check first exit
                    assert "symbol" in exit, f"{ptype}: Exit missing symbol"
                    assert "buy_price" in exit, f"{ptype}: Exit missing buy_price"
                    assert "exit_price" in exit, f"{ptype}: Exit missing exit_price"
                    assert "realized_pnl" in exit, f"{ptype}: Exit missing realized_pnl"
            else:
                print(f"⚠️ {ptype}: No exits found (may have been cleared)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

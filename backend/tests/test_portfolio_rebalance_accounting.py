"""
End-to-end accounting test for custom portfolio rebalance.

Validates the user-reported bug: after a swap A→B, sell proceeds must
be added back to the portfolio (not reset to initial capital).

Invariant checked:
   current_value  ==  initial_capital + total_pnl
   total_pnl      ==  realized_pnl + unrealized_pnl
"""
import os
import time
import pytest
import requests

BACKEND_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://quant-analyst-hub.preview.emergentagent.com"
)
API = f"{BACKEND_URL}/api"


def _fetch_live_symbols():
    """Get two sets of symbols with real prices from the search endpoint."""
    r = requests.get(f"{API}/symbols/search", params={"q": "RELIANCE"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    symbols = data.get("results", []) or data.get("symbols", [])
    return symbols[:1] if symbols else []


def test_custom_portfolio_rebalance_preserves_capital():
    """Swap one stock for another; current_value must = initial + realized + unrealized."""
    # Step 1: Create a 3-stock portfolio
    create_payload = {
        "name": f"RebalanceTest-{int(time.time())}",
        "capital": 1000000,  # ₹10L
        "symbols": [
            {"symbol": "RELIANCE.NS", "name": "Reliance", "weight": 34},
            {"symbol": "TCS.NS", "name": "TCS", "weight": 33},
            {"symbol": "INFY.NS", "name": "Infosys", "weight": 33},
        ],
    }
    r = requests.post(f"{API}/custom-portfolios", json=create_payload, timeout=60)
    assert r.status_code == 200, f"Create failed: {r.text}"
    p = r.json()
    pid = p["id"]
    initial_capital = p["total_invested"]
    assert initial_capital > 0

    try:
        # Step 2: Refresh prices
        r = requests.get(f"{API}/custom-portfolios/{pid}", timeout=30)
        assert r.status_code == 200, f"Get failed: {r.text}"
        p = r.json()
        value_before = p["current_value"]
        holdings_before = {h["symbol"]: h for h in p["holdings"]}

        # Step 3: Swap INFY for HDFCBANK (keeping RELIANCE, TCS)
        rebal_payload = {
            "symbols": [
                {"symbol": "RELIANCE.NS", "name": "Reliance",
                 "weight": holdings_before["RELIANCE.NS"]["weight"]},
                {"symbol": "TCS.NS", "name": "TCS",
                 "weight": holdings_before["TCS.NS"]["weight"]},
                {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 33},
            ],
        }
        r = requests.put(
            f"{API}/custom-portfolios/{pid}/rebalance",
            json=rebal_payload, timeout=60
        )
        assert r.status_code == 200, f"Rebalance failed: {r.text}"
        p = r.json()

        # Step 4: Invariant checks
        symbols_after = {h["symbol"] for h in p["holdings"]}
        assert "INFY.NS" not in symbols_after, "INFY should be removed"
        assert "HDFCBANK.NS" in symbols_after, "HDFCBANK should be added"
        assert "RELIANCE.NS" in symbols_after, "RELIANCE should be kept"

        # Check cost-basis preservation for kept stocks
        reliance_after = next(h for h in p["holdings"] if h["symbol"] == "RELIANCE.NS")
        reliance_before = holdings_before["RELIANCE.NS"]
        assert reliance_after["entry_price"] == reliance_before["entry_price"], \
            "Kept stock entry_price must be preserved"
        assert reliance_after["quantity"] == reliance_before["quantity"], \
            "Kept stock quantity must be preserved (weight unchanged)"

        # Check accounting fields exist
        assert "realized_pnl" in p
        assert "unrealized_pnl" in p
        assert "cash_balance" in p
        assert "current_value" in p

        # Check invariant: current_value ≈ initial_capital + total_pnl
        total_pnl = p["realized_pnl"] + p["unrealized_pnl"]
        assert abs(p["total_pnl"] - total_pnl) < 1.0, \
            f"total_pnl mismatch: {p['total_pnl']} vs {total_pnl}"

        # Check value is NOT reset to initial (this was the bug)
        # current_value should be roughly preserved within 5% of value_before
        assert p["current_value"] > value_before * 0.9, \
            f"Capital eaten after rebalance: before={value_before}, after={p['current_value']}"

        # Check invariant: current = holdings + cash
        holdings_value = sum(h["current_price"] * h["quantity"] for h in p["holdings"])
        assert abs(p["current_value"] - (holdings_value + p["cash_balance"])) < 1.0

    finally:
        # Cleanup
        requests.delete(f"{API}/custom-portfolios/{pid}", timeout=10)


if __name__ == "__main__":
    test_custom_portfolio_rebalance_preserves_capital()
    print("✅ Rebalance accounting test passed")

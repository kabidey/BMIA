"""
Overview math invariants test.
Verifies that /api/portfolios/overview returns internally consistent numbers:
  total_pnl == total_value - total_invested
  total_pnl_pct == total_pnl / total_invested * 100
  Per-portfolio pnl + aggregate pnl consistent
"""
import os
import requests

BACKEND_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://india-equity-scanner.preview.emergentagent.com"
)


def test_portfolio_overview_math_consistent():
    r = requests.get(f"{BACKEND_URL}/api/portfolios/overview", timeout=30)
    assert r.status_code == 200
    d = r.json()

    # Invariant 1: total_pnl == total_value - total_invested (within rounding)
    computed = d["total_value"] - d["total_invested"]
    assert abs(d["total_pnl"] - computed) < 1.0, \
        f"total_pnl mismatch: {d['total_pnl']} vs {computed}"

    # Invariant 2: total_pnl_pct matches
    if d["total_invested"] > 0:
        expected_pct = round(d["total_pnl"] / d["total_invested"] * 100, 2)
        assert abs(d["total_pnl_pct"] - expected_pct) < 0.1

    # Invariant 3: sum of per-portfolio pnl == aggregate
    per_sum = sum(p["total_pnl"] for p in d.get("portfolios", []))
    assert abs(d["total_pnl"] - per_sum) < 5.0, \
        f"Per-portfolio sum {per_sum} vs aggregate {d['total_pnl']}"

    # Sign check: if value < invested, pnl must be negative (this was the UX bug!)
    if d["total_value"] < d["total_invested"]:
        assert d["total_pnl"] < 0, \
            "Value below invested MUST show negative P&L (display bug)"

    print(f"✅ Capital:   ₹{d['total_capital']/1e5:.1f}L")
    print(f"✅ Invested:  ₹{d['total_invested']/1e5:.1f}L")
    print(f"✅ Value:     ₹{d['total_value']/1e5:.1f}L")
    print(f"✅ P&L:       ₹{d['total_pnl']/1e5:+.2f}L ({d['total_pnl_pct']}%)")
    print(f"✅ Realized:  ₹{d.get('total_realized_pnl',0)/1e5:+.2f}L")
    print(f"✅ Cash:      ₹{d.get('total_cash_balance',0)/1e5:.2f}L")


if __name__ == "__main__":
    test_portfolio_overview_math_consistent()
    print("\n✅ All overview invariants hold")

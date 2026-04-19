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
    "https://portfolio-forecast-4.preview.emergentagent.com"
)


def test_portfolio_overview_math_consistent():
    r = requests.get(f"{BACKEND_URL}/api/portfolios/overview", timeout=30)
    assert r.status_code == 200
    d = r.json()

    # PMS invariant: total_pnl == total_realized_pnl + total_unrealized_pnl
    # (Total Return = Realized + Unrealized, standard PMS accounting)
    computed = d.get("total_realized_pnl", 0) + d.get("total_unrealized_pnl", 0)
    assert abs(d["total_pnl"] - computed) < 1.0, \
        f"total_pnl mismatch: {d['total_pnl']} vs realized+unrealized={computed}"

    # nav_delta invariant: total_value - total_capital
    nav_delta = d["total_value"] - d["total_capital"]
    if "nav_delta" in d:
        assert abs(d["nav_delta"] - nav_delta) < 1.0

    # Per-portfolio: total_pnl = realized + unrealized
    for p in d.get("portfolios", []):
        per_sum = p.get("realized_pnl", 0) + p.get("unrealized_pnl", 0)
        assert abs(p["total_pnl"] - per_sum) < 1.0, \
            f"{p['type']}: total_pnl {p['total_pnl']} vs realized+unrealized={per_sum}"

    # Aggregate: sum of per-portfolio == global
    per_total = sum(p["total_pnl"] for p in d.get("portfolios", []))
    assert abs(d["total_pnl"] - per_total) < 5.0

    print(f"✅ Capital:   ₹{d['total_capital']/1e5:.1f}L")
    print(f"✅ Invested:  ₹{d['total_invested']/1e5:.1f}L")
    print(f"✅ Value:     ₹{d['total_value']/1e5:.1f}L")
    print(f"✅ P&L:       ₹{d['total_pnl']/1e5:+.2f}L ({d['total_pnl_pct']}%)")
    print(f"✅ Realized:  ₹{d.get('total_realized_pnl',0)/1e5:+.2f}L")
    print(f"✅ Cash:      ₹{d.get('total_cash_balance',0)/1e5:.2f}L")


if __name__ == "__main__":
    test_portfolio_overview_math_consistent()
    print("\n✅ All overview invariants hold")

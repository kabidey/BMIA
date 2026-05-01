"""
Reconcile portfolios damaged by the proceeds-double-booking bug
(`auto_reinvest.reinvest_proceeds` historically added the exit proceeds
to `cash_balance` AFTER `_enforce_stops` had already banked them, which
inflated `cash_balance`, `current_value`, and `total_pnl` by exactly the
exit proceeds for every successful stop-out + auto-reinvest pair).

Reconciliation invariant for autonomous strategy portfolios (no external
deposits/withdrawals):

    expected_cash = initial_capital
                  + realized_pnl
                  - sum(entry_price × quantity for h in holdings)

i.e. "what's left over after committing your capital and booking realized
gains is your cash". Any positive delta vs. the stored cash_balance is
inflation from the old bug; any negative delta is a different (older) bug
that this script will not touch.

Usage:
    python scripts/reconcile_inflated_reinvest.py                # DRY RUN
    python scripts/reconcile_inflated_reinvest.py --apply        # WRITE
    python scripts/reconcile_inflated_reinvest.py --apply --type momentum
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import pymongo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _expected_cash(p: dict) -> float:
    initial_capital = float(p.get("initial_capital", 0) or 0)
    realized_pnl = float(p.get("realized_pnl", 0) or 0)
    cost_basis = sum(
        float(h.get("entry_price", 0) or 0) * (h.get("quantity", 0) or 0)
        for h in p.get("holdings", [])
    )
    return initial_capital + realized_pnl - cost_basis


def reconcile(db, dry_run: bool, only_type: str | None) -> list[dict]:
    q = {"status": "active"}
    if only_type:
        q["type"] = only_type
    portfolios = list(db.portfolios.find(q))
    out = []

    for p in portfolios:
        ptype = p["type"]
        stored_cash = float(p.get("cash_balance", 0) or 0)
        expected = _expected_cash(p)
        delta = stored_cash - expected   # positive => inflated by bug

        # holdings_value at current prices (for current_value re-derivation)
        holdings_value = sum(
            float(h.get("current_price", h.get("entry_price", 0)) or 0)
            * (h.get("quantity", 0) or 0)
            for h in p.get("holdings", [])
        )
        current_value_now = holdings_value + stored_cash
        current_value_fixed = holdings_value + max(expected, 0.0)

        flag = "OK" if abs(delta) < 1.0 else ("INFLATED" if delta > 0 else "UNDER")
        print(
            f"\n[{ptype}] cash stored={stored_cash:>12,.2f} "
            f"expected={expected:>12,.2f} delta={delta:>+12,.2f}  "
            f"NAV {current_value_now:,.0f} -> {current_value_fixed:,.0f}  [{flag}]"
        )

        if delta <= 1.0:
            continue  # nothing to do (or under-counted, which is a different bug)

        # Recompute downstream fields with the fixed cash
        initial_capital = float(p.get("initial_capital", 0) or 0)
        unrealized_pnl = holdings_value - sum(
            float(h.get("entry_price", 0) or 0) * (h.get("quantity", 0) or 0)
            for h in p.get("holdings", [])
        )
        total_pnl = current_value_fixed - initial_capital
        total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

        update = {
            "cash_balance": round(max(expected, 0.0), 2),
            "current_value": round(current_value_fixed, 2),
            "holdings_value": round(holdings_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
            "reconcile_note": (
                f"Removed ₹{delta:,.2f} of double-booked reinvestment "
                f"proceeds (auto_reinvest pre-fix bug)."
            ),
        }
        record = {"portfolio": ptype, "delta_removed": round(delta, 2),
                  "old_cash": stored_cash, "new_cash": update["cash_balance"]}

        if dry_run:
            out.append({**record, "dry_run": True})
            continue

        db.portfolios.update_one({"type": ptype}, {"$set": update})
        db.portfolio_rebalance_log.insert_one({
            "portfolio_type": ptype,
            "action": "RECONCILE_INFLATED_REINVEST",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "delta_removed": round(delta, 2),
            "old_cash": stored_cash,
            "new_cash": update["cash_balance"],
            "old_current_value": round(current_value_now, 2),
            "new_current_value": update["current_value"],
            "note": update["reconcile_note"],
        })
        out.append({**record, "dry_run": False})
        print(f"  APPLIED: cash {stored_cash:,.2f} -> {update['cash_balance']:,.2f}")

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write the fix (default is dry run)")
    parser.add_argument("--type", default=None, help="Only reconcile a single strategy type")
    args = parser.parse_args()

    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    print("=== {} ===".format("APPLYING RECONCILIATION" if args.apply else "DRY RUN (use --apply to write)"))
    res = reconcile(db, dry_run=not args.apply, only_type=args.type)
    print(f"\n{'='*60}\nPortfolios touched: {len(res)}")
    client.close()


if __name__ == "__main__":
    main()

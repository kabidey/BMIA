"""
One-shot backfill: reconstruct realized_pnl + cash_balance + actual_invested
for AI portfolios that had historical STOP_ENFORCED events under the old buggy
daemon (which deleted holdings without banking proceeds).

Strategy:
  - For each AI portfolio with historical STOP_ENFORCED logs:
    - The stopped stock's weight = 100 - sum(current_holdings_weights)
      (since initial portfolios target 100% allocation and daemon didn't touch weights)
    - cost_basis_lost ≈ initial_capital × (lost_weight / 100)
    - pnl_pct is known from the log
    - realized_pnl_lost = cost_basis_lost × (pnl_pct / 100)
    - proceeds_lost = cost_basis_lost × (1 + pnl_pct / 100)
  - Credit proceeds to cash_balance
  - Credit gain to realized_pnl
  - Set actual_invested back to cost_basis_current + cost_basis_lost
  - Upgrade the historical log entry with derived fields

Safe to run once; idempotent via a `backfill_applied` flag on the log.
"""
import os
import sys
from datetime import datetime

import pymongo


def _sf(v, d=0.0):
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def backfill_ai_portfolios(db, dry_run=True):
    affected = []
    stop_logs = list(db.portfolio_rebalance_log.find(
        {"action": "STOP_ENFORCED"}
    ).sort("timestamp", 1))

    if not stop_logs:
        print("No STOP_ENFORCED logs found.")
        return []

    print(f"Found {len(stop_logs)} historical STOP_ENFORCED events")

    # Group by portfolio
    by_portfolio = {}
    for log in stop_logs:
        if log.get("backfill_applied"):
            print(f"  SKIP (already backfilled): {log.get('portfolio_type')} @ {log.get('timestamp')}")
            continue
        ptype = log["portfolio_type"]
        by_portfolio.setdefault(ptype, []).append(log)

    for ptype, logs in by_portfolio.items():
        p = db.portfolios.find_one({"type": ptype})
        if not p:
            print(f"  WARN: portfolio {ptype} not found, skipping")
            continue

        initial_capital = _sf(p.get("initial_capital", 5_000_000))
        actual_invested = _sf(p.get("actual_invested", 0))
        realized_pnl = _sf(p.get("realized_pnl", 0))
        cash_balance = _sf(p.get("cash_balance", 0))
        holdings = p.get("holdings", [])
        weight_sum_remaining = sum(_sf(h.get("weight", 0)) for h in holdings)

        # Lost weight across all stop events combined
        # (portfolio originally summed to ~100%, current remaining is weight_sum_remaining)
        total_lost_weight = max(0.0, 100.0 - weight_sum_remaining)

        if total_lost_weight <= 0.01:
            print(f"  {ptype}: weights already sum to ~100%, no gap to fill. Skipping.")
            continue

        # Distribute lost weight proportionally across the stop events
        # based on their pnl_pct-weighted cost basis (approximation).
        # Simple split: equal share per event.
        per_event_weight = total_lost_weight / len(logs)

        total_proceeds = 0.0
        total_realized = 0.0
        total_cost_basis = 0.0

        updates = []
        for log in logs:
            change = (log.get("changes") or [{}])[0]
            pnl_pct = _sf(change.get("pnl_pct", 0))
            symbol = change.get("symbol", "")
            cost_basis = initial_capital * (per_event_weight / 100.0)
            realized_gain = cost_basis * (pnl_pct / 100.0)
            proceeds = cost_basis + realized_gain

            total_cost_basis += cost_basis
            total_proceeds += proceeds
            total_realized += realized_gain

            updates.append({
                "log_id": log["_id"],
                "symbol": symbol,
                "pnl_pct": pnl_pct,
                "estimated_weight_pct": round(per_event_weight, 2),
                "estimated_cost_basis": round(cost_basis, 2),
                "estimated_realized_pnl": round(realized_gain, 2),
                "estimated_proceeds": round(proceeds, 2),
            })

        new_actual_invested = actual_invested + total_cost_basis
        new_realized_pnl = realized_pnl + total_realized
        new_cash_balance = cash_balance + total_proceeds

        # Compute fresh total_pnl + current_value
        holdings_value = sum(
            _sf(h.get("current_price", h.get("entry_price", 0))) * h.get("quantity", 0)
            for h in holdings
        )
        current_value = holdings_value + new_cash_balance
        unrealized_pnl = holdings_value - sum(
            _sf(h.get("entry_price", 0)) * h.get("quantity", 0) for h in holdings
        )
        total_pnl = new_realized_pnl + unrealized_pnl
        total_pnl_pct = (total_pnl / new_actual_invested * 100) if new_actual_invested > 0 else 0

        report = {
            "portfolio": ptype,
            "events": len(logs),
            "total_lost_weight_pct": round(total_lost_weight, 2),
            "cost_basis_restored": round(total_cost_basis, 2),
            "realized_pnl_added": round(total_realized, 2),
            "cash_balance_added": round(total_proceeds, 2),
            "before": {
                "actual_invested": actual_invested,
                "realized_pnl": realized_pnl,
                "cash_balance": cash_balance,
                "current_value": p.get("current_value"),
                "total_pnl": p.get("total_pnl"),
            },
            "after": {
                "actual_invested": round(new_actual_invested, 2),
                "realized_pnl": round(new_realized_pnl, 2),
                "cash_balance": round(new_cash_balance, 2),
                "current_value": round(current_value, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round(total_pnl_pct, 2),
            },
            "details": updates,
        }
        affected.append(report)

        print(f"\n{ptype}:")
        print(f"  Lost weight: {total_lost_weight:.2f}%")
        print(f"  + cost_basis: ₹{total_cost_basis:,.2f}")
        print(f"  + realized_pnl: ₹{total_realized:,.2f}")
        print(f"  + cash_balance: ₹{total_proceeds:,.2f}")
        print(f"  actual_invested: ₹{actual_invested:,.2f} → ₹{new_actual_invested:,.2f}")
        print(f"  current_value: ₹{p.get('current_value', 0):,.2f} → ₹{current_value:,.2f}")
        print(f"  total_pnl: ₹{p.get('total_pnl', 0):,.2f} → ₹{total_pnl:,.2f}")

        if not dry_run:
            db.portfolios.update_one(
                {"type": ptype},
                {"$set": {
                    "actual_invested": round(new_actual_invested, 2),
                    "realized_pnl": round(new_realized_pnl, 2),
                    "cash_balance": round(new_cash_balance, 2),
                    "current_value": round(current_value, 2),
                    "holdings_value": round(holdings_value, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "total_pnl": round(total_pnl, 2),
                    "total_pnl_pct": round(total_pnl_pct, 2),
                    "backfilled_at": datetime.now().isoformat(),
                }}
            )
            # Mark each log as backfilled with enriched data
            for u in updates:
                db.portfolio_rebalance_log.update_one(
                    {"_id": u["log_id"]},
                    {"$set": {
                        "backfill_applied": True,
                        "backfill_details": {
                            "estimated_weight_pct": u["estimated_weight_pct"],
                            "estimated_cost_basis": u["estimated_cost_basis"],
                            "estimated_realized_pnl": u["estimated_realized_pnl"],
                            "estimated_proceeds": u["estimated_proceeds"],
                            "note": "Backfilled from weight-gap + pnl_pct (exact entry/qty lost by old daemon)",
                        },
                        "changes.0.realized_pnl": u["estimated_realized_pnl"],
                        "changes.0.proceeds": u["estimated_proceeds"],
                        "changes.0.estimated": True,
                    }}
                )

    return affected


def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]

    dry_run = "--apply" not in sys.argv
    if dry_run:
        print("=== DRY RUN (use --apply to write) ===\n")
    else:
        print("=== APPLYING BACKFILL ===\n")

    result = backfill_ai_portfolios(db, dry_run=dry_run)

    print(f"\n{'='*60}")
    print(f"Affected portfolios: {len(result)}")
    if not dry_run and result:
        print("✅ Backfill applied successfully")

    client.close()


if __name__ == "__main__":
    main()

"""
Revert the portfolio accounting backfill.
Undoes /app/backend/scripts/backfill_portfolio_accounting.py by:
  - Resetting realized_pnl, cash_balance, holdings_value, unrealized_pnl to 0
  - Recomputing actual_invested from current holdings (sum of entry*qty)
  - Removing backfill_applied flag and backfill_details from log entries
  - Removing estimated fields from logged changes
"""
import os
import sys
import pymongo


def revert(db, dry_run=True):
    stop_logs = list(db.portfolio_rebalance_log.find({"backfill_applied": True}))
    affected_portfolios = set(log["portfolio_type"] for log in stop_logs)

    print(f"Found {len(stop_logs)} backfilled log entries across {len(affected_portfolios)} portfolios")

    for ptype in affected_portfolios:
        p = db.portfolios.find_one({"type": ptype})
        if not p:
            continue

        holdings = p.get("holdings", [])
        actual_invested = sum(
            float(h.get("entry_price", 0) or 0) * h.get("quantity", 0)
            for h in holdings
        )
        holdings_value = sum(
            float(h.get("current_price", h.get("entry_price", 0)) or 0) * h.get("quantity", 0)
            for h in holdings
        )
        total_pnl = holdings_value - actual_invested
        total_pnl_pct = (total_pnl / actual_invested * 100) if actual_invested > 0 else 0

        print(f"\n{ptype}:")
        print(f"  actual_invested: ₹{p.get('actual_invested',0):,.2f} → ₹{actual_invested:,.2f}")
        print(f"  current_value:   ₹{p.get('current_value',0):,.2f} → ₹{holdings_value:,.2f}")
        print(f"  realized_pnl:    ₹{p.get('realized_pnl',0):,.2f} → ₹0.00 (removed)")
        print(f"  cash_balance:    ₹{p.get('cash_balance',0):,.2f} → ₹0.00 (removed)")

        if not dry_run:
            db.portfolios.update_one(
                {"type": ptype},
                {"$set": {
                    "actual_invested": round(actual_invested, 2),
                    "current_value": round(holdings_value, 2),
                    "holdings_value": round(holdings_value, 2),
                    "cash_balance": 0.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": round(total_pnl, 2),
                    "total_pnl": round(total_pnl, 2),
                    "total_pnl_pct": round(total_pnl_pct, 2),
                },
                 "$unset": {"backfilled_at": ""}}
            )

    if not dry_run:
        # Clean up log entries
        db.portfolio_rebalance_log.update_many(
            {"backfill_applied": True},
            {"$unset": {
                "backfill_applied": "",
                "backfill_details": "",
                "changes.0.realized_pnl": "",
                "changes.0.proceeds": "",
                "changes.0.estimated": "",
            }}
        )
        print(f"\n✅ Reverted {len(affected_portfolios)} portfolios; stripped flags from {len(stop_logs)} log entries")


def main():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    dry_run = "--apply" not in sys.argv
    if dry_run:
        print("=== DRY RUN (use --apply to write) ===")
    else:
        print("=== APPLYING REVERT ===")
    revert(db, dry_run=dry_run)
    client.close()


if __name__ == "__main__":
    main()

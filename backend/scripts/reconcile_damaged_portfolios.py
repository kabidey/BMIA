"""
Reconcile damaged portfolios by forcefully deploying missing capital
into replacement stocks via the auto_reinvest picker.

Usage: python scripts/reconcile_damaged_portfolios.py [--apply]

For each portfolio where sum(holdings.weight) < 99%, computes the
"missing" capital (= initial_capital × lost_weight%) and picks a
replacement stock to fill the slot. Portfolio state after reconcile:
  - All weights sum to ~100%
  - No phantom cash
  - NAV ≈ initial_capital +/- MTM

Idempotent: only acts if lost_weight > 1%.
"""
import os
import sys

import pymongo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auto_reinvest import pick_replacement_stock  # noqa: E402


def reconcile(db, dry_run=True):
    portfolios = list(db.portfolios.find({"status": "active"}))
    affected = []

    for p in portfolios:
        ptype = p["type"]
        holdings = p.get("holdings", [])
        weight_sum = sum(float(h.get("weight", 0) or 0) for h in holdings)
        lost_weight = max(0.0, 100.0 - weight_sum)

        if lost_weight <= 1.0:
            print(f"  SKIP {ptype}: weights already sum to {weight_sum:.1f}%")
            continue

        capital = float(p.get("initial_capital", 5_000_000))
        holdings_value = sum(
            float(h.get("current_price", h.get("entry_price", 0)) or 0) * h.get("quantity", 0)
            for h in holdings
        )
        # The "phantom capital" = what the portfolio SHOULD have as deployable cash
        # if the old buggy daemon had banked proceeds properly.
        phantom_cash = capital * (lost_weight / 100.0)

        print(f"\n{ptype}: weight_sum={weight_sum:.1f}% lost={lost_weight:.1f}% → deploying ₹{phantom_cash:,.0f}")

        held = {h["symbol"] for h in holdings}
        replacement = pick_replacement_stock(held, phantom_cash)
        if not replacement:
            print(f"  FAIL: No viable replacement found for {ptype}")
            continue

        print(f"  PICK: {replacement['symbol']} @ ₹{replacement['current_price']} "
              f"× {replacement['quantity']} = ₹{replacement['deployed']:,.0f} "
              f"(score {replacement['score']}, 3M {replacement['ret_3m_pct']}%)")

        if dry_run:
            affected.append({"portfolio": ptype, "pick": replacement, "dry_run": True})
            continue

        from datetime import datetime
        new_holding = {
            "symbol": replacement["symbol"],
            "name": replacement["name"],
            "sector": replacement["sector"],
            "entry_price": replacement["current_price"],
            "current_price": replacement["current_price"],
            "quantity": replacement["quantity"],
            "weight": round(lost_weight, 1),
            "allocation": replacement["deployed"],
            "pnl": 0,
            "pnl_pct": 0,
            "conviction": "RECONCILE",
            "rationale": (f"Auto-redeployment of ₹{phantom_cash/1e5:.2f}L phantom capital "
                          f"(lost from pre-fix daemon bug). Momentum score {replacement['score']} "
                          f"(3M {replacement['ret_3m_pct']}%, 6M {replacement['ret_6m_pct']}%)."),
            "key_catalyst": "One-time portfolio reconciliation",
            "risk_flag": "",
            "entry_date": datetime.now().isoformat(),
        }
        new_holdings = holdings + [new_holding]
        # New actual_invested = current invested + deployed (restores the missing basis)
        new_actual_invested = float(p.get("actual_invested", capital)) + replacement["deployed"]
        new_holdings_value = holdings_value + replacement["deployed"]

        db.portfolios.update_one(
            {"type": ptype},
            {"$set": {
                "holdings": new_holdings,
                "actual_invested": round(new_actual_invested, 2),
                "holdings_value": round(new_holdings_value, 2),
                "current_value": round(new_holdings_value, 2),
            }}
        )

        db.portfolio_rebalance_log.insert_one({
            "portfolio_type": ptype,
            "action": "RECONCILE",
            "timestamp": datetime.now().isoformat(),
            "changes": [{
                "type": "IN",
                "symbol": replacement["symbol"],
                "name": replacement["name"],
                "sector": replacement["sector"],
                "entry_price": replacement["current_price"],
                "quantity": replacement["quantity"],
                "rationale": new_holding["rationale"],
            }],
            "note": f"Reconciled ₹{phantom_cash:,.0f} phantom capital from historical stop-outs",
        })

        affected.append({"portfolio": ptype, "pick": replacement, "dry_run": False})
        print(f"  APPLIED: {ptype} now at ~100% weight")

    return affected


def main():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    dry_run = "--apply" not in sys.argv

    if dry_run:
        print("=== DRY RUN (use --apply to write) ===\n")
    else:
        print("=== APPLYING RECONCILIATION ===\n")

    result = reconcile(db, dry_run=dry_run)
    print(f"\n{'='*60}")
    print(f"Affected portfolios: {len(result)}")
    client.close()


if __name__ == "__main__":
    main()

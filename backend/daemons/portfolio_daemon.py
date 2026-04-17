"""
Portfolio Daemon v3 — Robust autonomous engine with DB-driven kill switch.
Handles: price updates, stop-loss/take-profit enforcement, rebalancing.
Uses pymongo (sync) to avoid event loop lifecycle issues.
"""
import os
import time
import math
import logging
import threading
from datetime import datetime, timezone, timedelta

import pymongo

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# Daemon state — readable from API
daemon_state = {
    "status": "stopped",      # running | paused | stopped
    "last_action": None,
    "last_action_at": None,
    "cycle_count": 0,
    "errors": [],
}


def _sf(val, default=0.0):
    if val is None:
        return default
    try:
        v = float(val)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def _update_prices(db, portfolio):
    """Refresh current prices for all holdings using yfinance.

    IMPORTANT: Does NOT overwrite actual_invested (that is the immutable
    cost basis set at portfolio creation / rebalance). Computes total_pnl
    as realized + unrealized P&L, and current_value as holdings + cash.
    """
    import yfinance as yf
    holdings = portfolio.get("holdings", [])
    holdings_value = 0.0

    for h in holdings:
        sym = h.get("symbol", "")
        entry = _sf(h.get("entry_price"))
        qty = h.get("quantity", 0)

        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            if hist is not None and len(hist) > 0:
                price = _sf(float(hist["Close"].iloc[-1]))
                if price > 0:
                    h["current_price"] = round(price, 2)
                    h["value"] = round(price * qty, 2)
                    if entry > 0:
                        h["pnl_pct"] = round((price - entry) / entry * 100, 2)
                        h["pnl"] = round((price - entry) * qty, 2)
        except Exception:
            pass

        cp = _sf(h.get("current_price", entry))
        holdings_value += cp * qty
        time.sleep(0.3)

    cash_balance = _sf(portfolio.get("cash_balance", 0))
    realized_pnl = _sf(portfolio.get("realized_pnl", 0))
    total_value = holdings_value + cash_balance

    # actual_invested reflects currently deployed capital (may shrink over
    # time due to stop-outs). initial_capital is the IMMUTABLE user-committed
    # basis and is what P&L must be measured against.
    actual_invested = _sf(portfolio.get("actual_invested", 0))
    if actual_invested <= 0:
        # Backfill one-time: compute from holdings (first run only)
        actual_invested = sum(_sf(h.get("entry_price")) * h.get("quantity", 0) for h in holdings)

    initial_capital = _sf(portfolio.get("initial_capital", 5_000_000))

    unrealized_pnl = holdings_value - sum(_sf(h.get("entry_price")) * h.get("quantity", 0) for h in holdings)
    # HONEST P&L: current portfolio value vs committed capital
    total_pnl = total_value - initial_capital
    total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

    db.portfolios.update_one(
        {"type": portfolio["type"]},
        {"$set": {
            "holdings": holdings,
            "current_value": round(total_value, 2),
            "holdings_value": round(holdings_value, 2),
            "cash_balance": round(cash_balance, 2),
            "actual_invested": round(actual_invested, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "prices_updated_at": datetime.now(IST).isoformat(),
        }}
    )
    return total_value


def _enforce_stops(db, portfolio):
    """Enforce 8% stop-loss and 20% take-profit. Realizes P&L on exit.

    Sell proceeds are added to cash_balance; realized P&L is accumulated.
    """
    STOP_LOSS_PCT = -8.0
    TAKE_PROFIT_PCT = 20.0
    triggered = []

    holdings = portfolio.get("holdings", [])
    for h in holdings:
        pnl = _sf(h.get("pnl_pct"))
        sym = h.get("symbol", "")

        if pnl <= STOP_LOSS_PCT:
            triggered.append({"symbol": sym, "type": "STOP_LOSS", "pnl_pct": pnl,
                              "reason": f"Hit {STOP_LOSS_PCT}% hard stop"})
        elif pnl >= TAKE_PROFIT_PCT:
            triggered.append({"symbol": sym, "type": "TAKE_PROFIT", "pnl_pct": pnl,
                              "reason": f"Hit +{TAKE_PROFIT_PCT}% take-profit"})

    if triggered:
        trigger_map = {t["symbol"]: t for t in triggered}
        remove_syms = set(trigger_map.keys())

        # Realize P&L + bank proceeds to cash
        cash_balance = _sf(portfolio.get("cash_balance", 0))
        realized_pnl_total = _sf(portfolio.get("realized_pnl", 0))
        changes = []
        for h in holdings:
            if h["symbol"] not in remove_syms:
                continue
            cp = _sf(h.get("current_price", h.get("entry_price", 0)))
            ep = _sf(h.get("entry_price", 0))
            qty = h.get("quantity", 0)
            pnl_amt = (cp - ep) * qty
            pnl_pct = ((cp - ep) / ep * 100) if ep > 0 else 0
            realized_pnl_total += pnl_amt
            cash_balance += cp * qty
            t = trigger_map[h["symbol"]]
            changes.append({
                "type": "OUT",
                "symbol": h["symbol"],
                "name": h.get("name", ""),
                "quantity": qty,
                "entry_price": round(ep, 2),
                "exit_price": round(cp, 2),
                "proceeds": round(cp * qty, 2),
                "realized_pnl": round(pnl_amt, 2),
                "realized_pnl_pct": round(pnl_pct, 2),
                "trigger_type": t["type"],
                "rationale": t["reason"],
            })

        new_holdings = [h for h in holdings if h["symbol"] not in remove_syms]

        db.portfolios.update_one(
            {"type": portfolio["type"]},
            {"$set": {
                "holdings": new_holdings,
                "cash_balance": round(cash_balance, 2),
                "realized_pnl": round(realized_pnl_total, 2),
            }}
        )

        db.portfolio_rebalance_log.insert_one({
            "portfolio_type": portfolio["type"],
            "action": "STOP_ENFORCED",
            "timestamp": datetime.now(IST).isoformat(),
            "changes": changes,
            "realized_pnl_delta": round(sum(c["realized_pnl"] for c in changes), 2),
        })

        logger.info(
            f"DAEMON: {portfolio['type']} — {len(triggered)} stops triggered: {list(remove_syms)} "
            f"| realized ₹{sum(c['realized_pnl'] for c in changes):,.0f}"
        )

    return triggered


def _is_paused(db):
    """Check DB kill switch."""
    config = db.daemon_config.find_one({"type": "portfolio_daemon"})
    if config and config.get("paused"):
        return True
    return False


def _daemon_loop(mongo_url, db_name):
    """Main daemon loop — uses sync pymongo, no event loop issues."""
    logger.info("PORTFOLIO DAEMON v3: Starting (sync pymongo, DB kill switch)")
    daemon_state["status"] = "running"
    time.sleep(30)  # Initial settle

    while True:
        try:
            client = pymongo.MongoClient(mongo_url)
            db = client[db_name]

            # Check kill switch
            if _is_paused(db):
                daemon_state["status"] = "paused"
                daemon_state["last_action"] = "Paused via kill switch"
                daemon_state["last_action_at"] = datetime.now(IST).isoformat()
                client.close()
                time.sleep(60)
                continue

            daemon_state["status"] = "running"
            now = datetime.now(IST)
            hour = now.hour
            today_str = now.strftime("%Y-%m-%d")

            # Check if today is a holiday
            is_holiday = db.nse_holidays.find_one({"date": today_str})
            is_weekend = now.weekday() >= 5

            if is_holiday or is_weekend:
                daemon_state["last_action"] = f"Market closed ({'Holiday' if is_holiday else 'Weekend'})"
                daemon_state["last_action_at"] = now.isoformat()
                client.close()
                time.sleep(1800)
                continue

            # Get active portfolios
            portfolios = list(db.portfolios.find({"status": "active"}))

            if not portfolios:
                daemon_state["last_action"] = "No active portfolios"
                daemon_state["last_action_at"] = now.isoformat()
                client.close()
                time.sleep(300)
                continue

            # Phase 1: Update prices (9 AM - 4 PM IST, every 5 min cycle)
            if 9 <= hour <= 16:
                for p in portfolios:
                    if _is_paused(db):
                        break
                    try:
                        val = _update_prices(db, p)
                        daemon_state["last_action"] = f"Prices updated: {p['type']} (₹{val/1e5:.1f}L)"
                        daemon_state["last_action_at"] = datetime.now(IST).isoformat()
                    except Exception as e:
                        logger.debug(f"DAEMON: Price update failed {p['type']}: {e}")
                    time.sleep(5)

            # Phase 2: Enforce stop-loss/take-profit (during market hours)
            if 9 <= hour <= 16:
                for p in portfolios:
                    if _is_paused(db):
                        break
                    try:
                        # Re-read fresh data
                        fresh = db.portfolios.find_one({"type": p["type"], "status": "active"})
                        if fresh:
                            triggered = _enforce_stops(db, fresh)
                            if triggered:
                                daemon_state["last_action"] = f"Stops triggered: {p['type']} ({len(triggered)} exits)"
                                daemon_state["last_action_at"] = datetime.now(IST).isoformat()
                    except Exception as e:
                        logger.debug(f"DAEMON: Stop enforcement failed {p['type']}: {e}")

            # Phase 3: Rebalance evaluation (4 PM - 6 PM IST, max 1 per portfolio per day)
            if 16 <= hour <= 18:
                for p in portfolios:
                    if _is_paused(db):
                        break
                    # Check if already rebalanced today
                    already = db.portfolio_rebalance_log.find_one({
                        "portfolio_type": p["type"],
                        "timestamp": {"$regex": today_str},
                    })
                    if already:
                        continue

                    daemon_state["last_action"] = f"Evaluating rebalance: {p['type']}"
                    daemon_state["last_action_at"] = datetime.now(IST).isoformat()
                    logger.info(f"DAEMON: Evaluating rebalance for {p['type']}")

                    # For rebalance we need async — use a fresh event loop just for this call
                    import asyncio
                    from motor.motor_asyncio import AsyncIOMotorClient
                    from services.portfolio_engine import evaluate_rebalancing
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        async_client = AsyncIOMotorClient(mongo_url)
                        async_db = async_client[db_name]
                        result = loop.run_until_complete(evaluate_rebalancing(async_db, p["type"]))
                        action = result.get("action", "unknown")
                        daemon_state["last_action"] = f"Rebalanced: {p['type']} → {action}"
                        daemon_state["last_action_at"] = datetime.now(IST).isoformat()
                        logger.info(f"DAEMON: Rebalance {p['type']}: {action}")
                        async_client.close()
                        try:
                            loop.run_until_complete(loop.shutdown_default_executor())
                        except Exception:
                            pass
                        loop.close()
                    except Exception as e:
                        logger.error(f"DAEMON: Rebalance failed {p['type']}: {e}")
                        try:
                            loop.close()
                        except Exception:
                            pass

                    time.sleep(10)

            daemon_state["cycle_count"] += 1
            client.close()

        except Exception as e:
            logger.error(f"DAEMON: Cycle error: {e}")
            daemon_state["errors"].append({"error": str(e), "at": datetime.now(IST).isoformat()})
            if len(daemon_state["errors"]) > 20:
                daemon_state["errors"] = daemon_state["errors"][-10:]

        # Sleep: 5 min during market hours, 30 min off hours
        now = datetime.now(IST)
        if 9 <= now.hour <= 18:
            time.sleep(300)
        else:
            time.sleep(1800)


def start_portfolio_daemon(mongo_url: str, db_name: str):
    """Launch the daemon thread."""
    t = threading.Thread(target=_daemon_loop, args=(mongo_url, db_name), daemon=True)
    t.start()
    logger.info("PORTFOLIO DAEMON v3: Thread launched")

"""Fund Management Daemon.

Continuously feeds NIFTY-500 (top-N by traded value) stocks through the
6-agent fund management pipeline, recording every accept/reject decision
to `fund_decisions` for an always-on research desk.

Architecture
────────────
  ┌────────────┐    enqueue     ┌────────────┐   pull-1     ┌────────────┐
  │ NSE bhav   │ ─────────────▶ │ fund_queue │ ───────────▶ │  pipeline  │
  │ universe   │  cycle every    │  (mongo)   │   1 / N s    │  6 agents  │
  └────────────┘   `interval`s   └────────────┘              └─────┬──────┘
                                                                   │
                                              persist verdict ◀────┤
                                                                   │
                                       fund_runs + fund_decisions ◀┘

Configurable via `db.daemon_config` (`type=fund_management_daemon`):
  • paused              kill switch (default false)
  • interval_seconds    sleep between stocks (default 60s)
  • universe_size       top-N by traded value (default 500)
  • only_market_hours   gate to 09–16 IST (default false — 24×7 by default
                        because LLM analysis doesn't depend on live trading)
  • cooldown_hours      don't re-analyse the same stock within X hours
                        (default 12, prevents loops on small universes)
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


# ─── Daemon state (read by /api/funds/daemon/status) ──────────────────────
daemon_state = {
    "status": "stopped",         # running | paused | stopped | sleeping
    "current_symbol": None,
    "last_action": None,
    "last_action_at": None,
    "decisions_count": 0,
    "accepts": 0,
    "rejects": 0,
    "holds": 0,
    "errors": [],
    "cycle_count": 0,
    "started_at": None,
}


DEFAULT_CFG = {
    "paused": False,
    "interval_seconds": 60,
    "universe_size": 500,
    "only_market_hours": False,
    "cooldown_hours": 12,
}


def _get_cfg(db) -> dict:
    cfg = db.daemon_config.find_one({"type": "fund_management_daemon"}) or {}
    out = dict(DEFAULT_CFG)
    out.update({k: v for k, v in cfg.items() if k in DEFAULT_CFG})
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_error(msg: str):
    daemon_state["errors"].append({"error": msg[:200], "at": _now_iso()})
    if len(daemon_state["errors"]) > 30:
        daemon_state["errors"] = daemon_state["errors"][-15:]


# ─── Universe builder (NIFTY-500 proxy: top-N by traded value) ────────────
def _build_universe(top_n: int) -> List[str]:
    """Return up to `top_n` NSE EQ symbols (e.g. RELIANCE.NS) ranked by
    daily traded value. Falls back to the auto_reinvest static list if
    the bhav copy is unreachable."""
    try:
        from services.full_market_scanner import get_nse_universe
        nse = get_nse_universe()
        if nse and len(nse) > 50:
            nse_sorted = sorted(nse, key=lambda x: x.get("traded_value", 0), reverse=True)
            return [s["symbol"] for s in nse_sorted[:top_n]]
    except Exception as e:
        logger.warning(f"FUND DAEMON: NSE universe fetch failed ({e}), falling back")
    try:
        from services.auto_reinvest import FALLBACK_UNIVERSE
        return list(FALLBACK_UNIVERSE)[:top_n]
    except Exception as e:
        logger.error(f"FUND DAEMON: fallback universe load failed ({e})")
        return []


# ─── Queue helpers ────────────────────────────────────────────────────────
def _refill_queue(db, top_n: int, cooldown_hours: int) -> int:
    """If the queue is empty, enqueue every NIFTY-N stock the daemon hasn't
    processed in the last `cooldown_hours` hours. Returns count enqueued."""
    if db.fund_queue.count_documents({"status": "queued"}) > 0:
        return 0
    universe = _build_universe(top_n)
    if not universe:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)).isoformat()
    recent = {d["symbol"] for d in db.fund_decisions.find(
        {"source": "daemon", "ts": {"$gte": cutoff}},
        {"_id": 0, "symbol": 1},
    )}
    fresh = [s for s in universe if s not in recent]
    if not fresh:
        # Cooldown pass — accept whole universe again
        fresh = universe
    rows = [{
        "symbol": sym, "status": "queued", "priority": 0,
        "queued_at": _now_iso(), "source": "daemon_cycle",
    } for sym in fresh]
    if rows:
        try:
            db.fund_queue.insert_many(rows, ordered=False)
        except Exception as e:
            logger.warning(f"FUND DAEMON: queue insert error: {e}")
    logger.info(f"FUND DAEMON: refilled queue with {len(rows)} symbols")
    return len(rows)


def _claim_next(db) -> Optional[dict]:
    """Atomically pull one queued symbol and mark it running."""
    return db.fund_queue.find_one_and_update(
        {"status": "queued"},
        {"$set": {"status": "running", "claimed_at": _now_iso()}},
        sort=[("priority", -1), ("queued_at", 1)],
    )


def _recover_stale_claims(db, stale_minutes: int = 10) -> int:
    """Re-queue rows stuck in `status=running` from a previous daemon
    instance that died (hot reload, OOM, restart). The pipeline writes a
    decision row on success, so any `running` queue row older than
    `stale_minutes` belongs to a dead worker."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)).isoformat()
    res = db.fund_queue.update_many(
        {"status": "running", "claimed_at": {"$lt": cutoff}},
        {"$set": {"status": "queued", "claimed_at": None,
                  "recovered_at": _now_iso()}},
    )
    if res.modified_count:
        logger.info(f"FUND DAEMON: recovered {res.modified_count} stale claims back to queued")
    return res.modified_count


def _release(db, queue_row, status: str, run_id: Optional[str], error: Optional[str] = None):
    db.fund_queue.update_one(
        {"_id": queue_row["_id"]},
        {"$set": {"status": status, "completed_at": _now_iso(),
                  "run_id": run_id, "error": (error or "")[:300]}},
    )


# ─── Pipeline runner (sync wrapper around the async pipeline) ─────────────
def _run_one(mongo_url: str, db_name: str, symbol: str) -> Optional[str]:
    """Spawn a fresh event loop, run the pipeline, return run_id."""
    from routes.fund_management import _run_pipeline

    run_id = uuid.uuid4().hex[:16]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    motor = AsyncIOMotorClient(mongo_url)
    try:
        adb = motor[db_name]
        loop.run_until_complete(adb.fund_runs.insert_one({
            "run_id": run_id,
            "symbol": symbol,
            "source": "daemon",
            "user_email": None,
            "horizon_hint": "swing",
            "status": "running",
            "current_stage": "queued",
            "stages": {},
            "events": [],
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }))
        loop.run_until_complete(_run_pipeline(run_id, symbol, None, "daemon"))
    finally:
        try:
            motor.close()
        except Exception:
            pass
        try:
            loop.run_until_complete(loop.shutdown_default_executor())
        except Exception:
            pass
        try:
            loop.close()
        except Exception:
            pass
    return run_id


def _is_market_hours_now() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour <= 16


# ─── Main daemon loop ─────────────────────────────────────────────────────
def _daemon_loop(mongo_url: str, db_name: str):
    logger.info("FUND DAEMON: starting (sync pymongo, DB kill switch, queue-driven)")
    daemon_state["status"] = "running"
    daemon_state["started_at"] = _now_iso()
    time.sleep(45)  # let the rest of the backend boot

    while True:
        try:
            client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            db = client[db_name]
            cfg = _get_cfg(db)

            if cfg["paused"]:
                daemon_state["status"] = "paused"
                daemon_state["last_action"] = "Paused via kill switch"
                daemon_state["last_action_at"] = _now_iso()
                client.close()
                time.sleep(30)
                continue

            if cfg["only_market_hours"] and not _is_market_hours_now():
                daemon_state["status"] = "sleeping"
                daemon_state["last_action"] = "Outside market hours"
                daemon_state["last_action_at"] = _now_iso()
                client.close()
                time.sleep(600)
                continue

            daemon_state["status"] = "running"

            # Recover any rows stuck in `running` from a previous worker
            _recover_stale_claims(db, stale_minutes=10)

            # Refill queue on demand
            _refill_queue(db, cfg["universe_size"], cfg["cooldown_hours"])

            row = _claim_next(db)
            if not row:
                daemon_state["last_action"] = "Queue empty, refilling next cycle"
                daemon_state["last_action_at"] = _now_iso()
                client.close()
                time.sleep(60)
                continue

            sym = row["symbol"]
            daemon_state["current_symbol"] = sym
            daemon_state["last_action"] = f"Analyzing {sym}"
            daemon_state["last_action_at"] = _now_iso()
            logger.info(f"FUND DAEMON: pulling {sym}")
            client.close()

            run_id = None
            err = None
            try:
                run_id = _run_one(mongo_url, db_name, sym)
            except Exception as e:
                err = str(e)
                logger.warning(f"FUND DAEMON: run for {sym} failed: {e}")
                _record_error(f"{sym}: {e}")

            # Look up the decision row (pipeline always logs one on success)
            client = pymongo.MongoClient(mongo_url)
            db = client[db_name]
            decision = None
            if run_id:
                d = db.fund_decisions.find_one({"run_id": run_id}, {"_id": 0, "decision": 1})
                if d:
                    decision = d.get("decision")
            _release(db, row, "completed" if run_id else "error", run_id, err)

            if decision == "ACCEPT":
                daemon_state["accepts"] += 1
            elif decision == "REJECT":
                daemon_state["rejects"] += 1
            elif decision == "HOLD":
                daemon_state["holds"] += 1
            daemon_state["decisions_count"] = (
                daemon_state["accepts"] + daemon_state["rejects"] + daemon_state["holds"]
            )
            daemon_state["last_action"] = (
                f"{sym} → {decision or 'ERROR'} (run {run_id or '–'})"
            )
            daemon_state["last_action_at"] = _now_iso()
            daemon_state["cycle_count"] += 1
            client.close()

            # Sleep between symbols to respect LLM rate limits / spread load
            time.sleep(max(15, int(cfg["interval_seconds"])))

        except Exception as e:
            logger.exception(f"FUND DAEMON: cycle error: {e}")
            _record_error(str(e))
            time.sleep(60)


def start_fund_management_daemon(mongo_url: str, db_name: str):
    t = threading.Thread(target=_daemon_loop, args=(mongo_url, db_name), daemon=True)
    t.start()
    logger.info("FUND DAEMON: thread launched")

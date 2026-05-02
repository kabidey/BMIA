"""Fund Management routes — hardened 6-agent pipeline orchestrator.

Endpoints
─────────
POST /api/funds/analyze        → kicks off pipeline, returns run_id
GET  /api/funds/stream/{id}    → SSE stream of agent events for a run
GET  /api/funds/runs           → list recent runs (decisions history)
GET  /api/funds/runs/{id}      → single run's full output
GET  /api/funds/decisions      → flat decision log (manual + daemon)
GET  /api/funds/daemon/status  → fund-management daemon state
POST /api/funds/daemon/{start,stop,pause}
POST /api/funds/daemon/feed    → manually enqueue a symbol for the daemon

Hardening guarantees
────────────────────
1. EVERY pipeline step is exception-isolated. A single failure (LLM error,
   bad data, network blip) cannot prevent downstream stages from running.
2. Pipelines that crash mid-run leave the DB in `status=running`. On
   backend boot, `_recover_orphaned_runs()` flips any `running` row whose
   `updated_at` is older than 8 minutes to `status=orphaned`.
3. Each completed run snapshots a flat row into `fund_decisions` so the
   daemon's history can be served fast without fetching the heavy stages.
4. SSE stream times out after 10 minutes so clients never hang forever.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from services import fund_agents as agents
from services import fund_data_tools as tools

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/funds", tags=["fund-management"])


# ─── Helpers ───────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(x: Any) -> Dict:
    """Coerce any orchestration result (exception | None | dict) into a dict
    so downstream agents always see a well-formed structure."""
    if isinstance(x, Exception):
        return {"error": str(x)[:200]}
    if not isinstance(x, dict):
        return {"value": x}
    return x


def _accept_reject(verdict: Dict) -> str:
    """Bucket the fund-manager's verdict into ACCEPT / REJECT / HOLD for
    daemon-style filtering. Anything other than a clean buy is REJECT."""
    fv = (verdict or {}).get("final_verdict") or ""
    if fv in ("STRONG_BUY", "BUY"):
        return "ACCEPT"
    if fv == "HOLD":
        return "HOLD"
    return "REJECT"


# ─── Request/response models ───────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    symbol: str
    user_email: Optional[str] = None
    horizon_hint: Optional[str] = None
    source: Optional[str] = "manual"   # "manual" | "daemon" | "api"


class DaemonControlRequest(BaseModel):
    action: str            # "start" | "stop" | "pause"
    interval_seconds: Optional[int] = None
    universe_size: Optional[int] = None
    only_market_hours: Optional[bool] = None


class FeedRequest(BaseModel):
    symbol: str
    priority: Optional[int] = 0


# ─── Pipeline orchestrator (every step is exception-isolated) ─────────────
async def _run_pipeline(run_id: str, symbol: str, user_email: Optional[str],
                        source: str = "manual") -> None:
    """Execute the 6-agent pipeline end to end.

    Hardening rules:
      • every async step is wrapped in try/except and ALWAYS produces a
        usable dict downstream (degraded if needed). The pipeline never
        early-exits because of one bad step.
      • final state is ALWAYS written: success → status=completed, hard
        failure → status=error.
      • `fund_decisions` row is appended regardless of degradation, so the
        daemon's history shows every attempt.
    """
    import pymongo
    sync_client = pymongo.MongoClient(os.environ["MONGO_URL"])
    sync_db = sync_client[os.environ["DB_NAME"]]
    motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = motor_client[os.environ["DB_NAME"]]
    sid = f"fund-{run_id}"

    async def _patch(stage: str, **fields):
        try:
            await db.fund_runs.update_one(
                {"run_id": run_id},
                {"$set": {f"stages.{stage}": fields, "current_stage": stage,
                          "updated_at": _now()},
                 "$push": {"events": {"stage": stage, "ts": _now(), **fields}}},
            )
        except Exception as e:
            logger.warning(f"FUND pipeline {run_id}: _patch({stage}) failed: {e}")

    async def _safe_step(name: str, coro, default: Dict | None = None):
        """Run an awaitable, logging+swallowing any exception so the
        pipeline always advances to the next step."""
        try:
            return await coro
        except Exception as e:
            logger.warning(f"FUND pipeline {run_id}: step {name} failed: {e}")
            return default if default is not None else {"error": str(e)[:200]}

    def _sync_step(name: str, fn, *args, default: Dict | None = None):
        try:
            return fn(*args)
        except Exception as e:
            logger.warning(f"FUND pipeline {run_id}: data tool {name} failed: {e}")
            return default if default is not None else {"ok": False, "error": str(e)[:200]}

    try:
        # ── Step 0: gather data in parallel ──
        await _patch("data_gathering", status="running")

        fundamentals_t = asyncio.to_thread(_sync_step, "fundamentals", tools.fetch_fundamentals, symbol)
        technicals_t = asyncio.to_thread(_sync_step, "technicals", tools.fetch_technicals, symbol)
        sentiment_t = asyncio.to_thread(_sync_step, "sentiment", tools.fetch_sentiment, sync_db,
                                        default={"ok": False, "fii_dii_5d": []})
        news_t = asyncio.to_thread(_sync_step, "news", tools.fetch_news, sync_db, symbol,
                                   default=[])
        portfolio_t = asyncio.to_thread(_sync_step, "portfolio", tools.fetch_portfolio_context,
                                        sync_db, user_email, default={"ok": False})
        compliance_t = _safe_step("compliance", tools.fetch_compliance_signal(symbol),
                                  default={"ok": False, "n_hits": 0, "regulatory_hits": []})

        fundamentals, technicals, sentiment, news_items, portfolio, compliance = await asyncio.gather(
            fundamentals_t, technicals_t, sentiment_t, news_t, portfolio_t, compliance_t,
            return_exceptions=True,
        )
        fundamentals = _safe(fundamentals)
        technicals = _safe(technicals)
        sentiment = _safe(sentiment)
        if isinstance(news_items, list) is False:
            news_items = []
        portfolio = _safe(portfolio)
        compliance = _safe(compliance)

        await _patch("data_gathering", status="done",
                     fundamentals_ok=bool(fundamentals.get("ok")),
                     technicals_ok=bool(technicals.get("ok")),
                     sentiment_ok=bool(sentiment.get("ok")),
                     news_count=len(news_items or []),
                     compliance_hits=int(compliance.get("n_hits", 0) or 0))

        # ── Step 1: 4 analysts in parallel — exception-isolated ──
        await _patch("analysts", status="running")
        analyst_outputs = await asyncio.gather(
            _safe_step("analyst.fundamentals",
                       agents.analyst_fundamentals(symbol, fundamentals, sid)),
            _safe_step("analyst.sentiment",
                       agents.analyst_sentiment(symbol, sentiment, sid)),
            _safe_step("analyst.news",
                       agents.analyst_news(symbol, news_items, sid)),
            _safe_step("analyst.technical",
                       agents.analyst_technical(symbol, technicals, sid)),
        )
        analysts_dict = {
            "fundamentals": _safe(analyst_outputs[0]),
            "sentiment":    _safe(analyst_outputs[1]),
            "news":         _safe(analyst_outputs[2]),
            "technical":    _safe(analyst_outputs[3]),
        }
        await _patch("analysts", status="done", **analysts_dict)

        # ── Step 2: bull vs bear debate (parallel) ──
        await _patch("debate", status="running")
        bull, bear = await asyncio.gather(
            _safe_step("bull", agents.researcher_bull(symbol, analysts_dict, sid)),
            _safe_step("bear", agents.researcher_bear(symbol, analysts_dict, sid)),
        )
        debate = {"bull": _safe(bull), "bear": _safe(bear)}
        await _patch("debate", status="done", **debate)

        # ── Step 3: trader ──
        await _patch("trader", status="running")
        last_price = technicals.get("last_close") if isinstance(technicals, dict) else None
        trade_proposal = _safe(await _safe_step(
            "trader", agents.trader(symbol, analysts_dict, debate, last_price, sid)
        ))
        await _patch("trader", status="done", **trade_proposal)

        # ── Step 4: risk manager ──
        await _patch("risk", status="running")
        risk_review = _safe(await _safe_step(
            "risk", agents.risk_manager(symbol, trade_proposal, portfolio, compliance, sid)
        ))
        await _patch("risk", status="done", **risk_review)

        # ── Step 5: fund manager (final verdict) ──
        await _patch("fund_manager", status="running")
        all_outputs = {
            "analysts": analysts_dict,
            "debate": debate,
            "trader": trade_proposal,
            "risk": risk_review,
            "data": {"fundamentals": fundamentals, "technicals": technicals,
                     "sentiment": sentiment, "compliance": compliance,
                     "portfolio": portfolio},
        }
        verdict = _safe(await _safe_step(
            "fund_manager", agents.fund_manager(symbol, all_outputs, sid)
        ))
        # Guarantee the verdict has the canonical fields the UI relies on
        verdict.setdefault("final_verdict", "HOLD")
        verdict.setdefault("confidence", 0.3)
        verdict.setdefault("headline",
                           f"{verdict.get('final_verdict')} — automated decision (degraded data)")

        await _patch("fund_manager", status="done", **verdict)

        await db.fund_runs.update_one(
            {"run_id": run_id},
            {"$set": {"final_verdict": verdict, "status": "completed",
                      "completed_at": _now()}},
        )

        # ── Persist a flat decision row for fast history queries ──
        decision_row = {
            "run_id": run_id,
            "symbol": symbol,
            "source": source,
            "user_email": user_email,
            "decision": _accept_reject(verdict),
            "final_verdict": verdict.get("final_verdict"),
            "confidence": verdict.get("confidence"),
            "headline": verdict.get("headline"),
            "approved_action": verdict.get("approved_action"),
            "rationale": (verdict.get("rationale") or "")[:1200],
            "key_reasons": (verdict.get("key_reasons") or [])[:5],
            "watch_outs": (verdict.get("watch_outs") or [])[:5],
            "sector": (fundamentals.get("sector") if isinstance(fundamentals, dict) else None),
            "last_close": (technicals.get("last_close") if isinstance(technicals, dict) else None),
            "rsi14": (technicals.get("rsi14") if isinstance(technicals, dict) else None),
            "fundamentals_ok": bool(fundamentals.get("ok")),
            "technicals_ok": bool(technicals.get("ok")),
            "compliance_hits": int(compliance.get("n_hits", 0) or 0),
            "ts": _now(),
        }
        try:
            await db.fund_decisions.insert_one(decision_row)
        except Exception as e:
            logger.warning(f"FUND pipeline {run_id}: decision log insert failed: {e}")

        logger.info(
            f"FUND pipeline [{run_id}] {symbol}: "
            f"{verdict.get('final_verdict')} ({decision_row['decision']}, "
            f"conf={verdict.get('confidence')})"
        )

    except Exception as e:
        logger.exception(f"FUND pipeline {run_id} top-level crashed")
        try:
            await db.fund_runs.update_one(
                {"run_id": run_id},
                {"$set": {"status": "error", "error": str(e)[:400],
                          "completed_at": _now()}},
            )
        except Exception:
            pass
    finally:
        try:
            sync_client.close()
        except Exception:
            pass
        try:
            motor_client.close()
        except Exception:
            pass


# ─── Orphan recovery (called from server lifespan) ─────────────────────────
async def recover_orphaned_runs(db) -> int:
    """Mark stuck `running` rows as `orphaned` if they haven't been updated
    in the last 8 minutes. Pipelines die when the backend restarts (the
    in-process asyncio task is killed) so this prevents zombie rows from
    showing as "running" forever in the UI."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=8)).isoformat()
    try:
        res = await db.fund_runs.update_many(
            {"status": "running", "updated_at": {"$lt": cutoff}},
            {"$set": {"status": "orphaned",
                      "error": "Backend restarted before pipeline finished",
                      "completed_at": _now()}},
        )
        if res.modified_count:
            logger.info(f"FUND recover: marked {res.modified_count} stuck runs as orphaned")
        return res.modified_count
    except Exception as e:
        logger.warning(f"FUND recover_orphaned_runs failed: {e}")
        return 0


# ─── Endpoints ─────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    if not req.symbol or len(req.symbol.strip()) < 1:
        raise HTTPException(400, "symbol required")
    run_id = uuid.uuid4().hex[:16]
    symbol = req.symbol.strip().upper()
    db = request.app.db
    await db.fund_runs.insert_one({
        "run_id": run_id,
        "symbol": symbol,
        "user_email": req.user_email,
        "horizon_hint": req.horizon_hint,
        "source": req.source or "manual",
        "status": "running",
        "current_stage": "queued",
        "stages": {},
        "events": [],
        "created_at": _now(),
        "updated_at": _now(),
    })
    asyncio.create_task(_run_pipeline(run_id, symbol, req.user_email, req.source or "manual"))
    return {"run_id": run_id, "status": "running"}


@router.get("/stream/{run_id}")
async def stream(run_id: str, request: Request):
    db = request.app.db

    async def event_gen():
        last_event_idx = -1
        for _ in range(600):  # max 10 minutes
            run = await db.fund_runs.find_one({"run_id": run_id}, {"_id": 0})
            if not run:
                yield f"event: error\ndata: {json.dumps({'error': 'run not found'})}\n\n"
                return
            events = run.get("events") or []
            for ev in events[last_event_idx + 1:]:
                yield f"event: stage\ndata: {json.dumps(ev, default=str)}\n\n"
            last_event_idx = len(events) - 1
            if run.get("status") in ("completed", "error", "orphaned"):
                yield ("event: done\ndata: " +
                       json.dumps({"status": run.get("status"),
                                   "final_verdict": run.get("final_verdict")},
                                  default=str) + "\n\n")
                return
            await asyncio.sleep(1)
        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request):
    run = await request.app.db.fund_runs.find_one({"run_id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.get("/runs")
async def list_runs(request: Request, limit: int = 20):
    cursor = request.app.db.fund_runs.find(
        {}, {"_id": 0, "events": 0},
    ).sort("created_at", -1).limit(min(limit, 100))
    return {"runs": await cursor.to_list(length=limit)}


@router.get("/decisions")
async def list_decisions(request: Request, limit: int = 50,
                         decision: Optional[str] = None,
                         source: Optional[str] = None,
                         symbol: Optional[str] = None):
    """Flat decision history — fast feed for the daemon dashboard."""
    q: Dict[str, Any] = {}
    if decision:
        q["decision"] = decision.upper()
    if source:
        q["source"] = source
    if symbol:
        q["symbol"] = symbol.upper()
    cursor = request.app.db.fund_decisions.find(q, {"_id": 0}).sort("ts", -1)\
        .limit(min(limit, 200))
    decisions = await cursor.to_list(length=limit)
    counts = {}
    for d in decisions:
        counts[d.get("decision", "UNKNOWN")] = counts.get(d.get("decision", "UNKNOWN"), 0) + 1
    return {"decisions": decisions, "counts": counts}


# ─── Daemon control endpoints ─────────────────────────────────────────────
@router.get("/daemon/status")
async def daemon_status(request: Request):
    from daemons.fund_management_daemon import daemon_state
    cfg = await request.app.db.daemon_config.find_one(
        {"type": "fund_management_daemon"}, {"_id": 0}) or {}
    queue_count = await request.app.db.fund_queue.count_documents({"status": "queued"})
    in_flight = await request.app.db.fund_queue.count_documents({"status": "running"})
    completed = await request.app.db.fund_decisions.count_documents({"source": "daemon"})
    return {
        "state": daemon_state,
        "config": cfg,
        "queued": queue_count,
        "in_flight": in_flight,
        "decisions_logged": completed,
    }


@router.post("/daemon/control")
async def daemon_control(req: DaemonControlRequest, request: Request):
    if req.action not in ("start", "stop", "pause"):
        raise HTTPException(400, "action must be start|stop|pause")
    update: Dict[str, Any] = {"updated_at": _now()}
    if req.action == "start":
        update["paused"] = False
    elif req.action in ("stop", "pause"):
        update["paused"] = True
    if req.interval_seconds is not None:
        update["interval_seconds"] = max(15, int(req.interval_seconds))
    if req.universe_size is not None:
        update["universe_size"] = max(50, min(1000, int(req.universe_size)))
    if req.only_market_hours is not None:
        update["only_market_hours"] = bool(req.only_market_hours)
    await request.app.db.daemon_config.update_one(
        {"type": "fund_management_daemon"},
        {"$set": update}, upsert=True,
    )
    return {"ok": True, "action": req.action, "config": update}


@router.post("/daemon/feed")
async def daemon_feed(req: FeedRequest, request: Request):
    """Manually push a symbol into the daemon queue."""
    sym = (req.symbol or "").strip().upper()
    if not sym:
        raise HTTPException(400, "symbol required")
    await request.app.db.fund_queue.update_one(
        {"symbol": sym, "status": "queued"},
        {"$set": {"symbol": sym, "status": "queued",
                  "priority": int(req.priority or 0),
                  "queued_at": _now(), "source": "manual"}},
        upsert=True,
    )
    return {"ok": True, "symbol": sym}

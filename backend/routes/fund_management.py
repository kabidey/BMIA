"""Fund Management routes — 6-agent pipeline orchestrator.

POST /api/funds/analyze        → kicks off pipeline, returns run_id
GET  /api/funds/stream/{id}    → SSE stream of agent events for a run
GET  /api/funds/runs           → list recent runs (decisions history)
GET  /api/funds/runs/{id}      → single run's full output

The pipeline runs in a background asyncio task so the POST can return
immediately and the SSE stream picks up events as agents finish. Events are
persisted to `fund_runs` so the UI can re-attach if the connection drops.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from services import fund_data_tools as tools
from services import fund_agents as agents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/funds", tags=["fund-management"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Request/response models ───────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    symbol: str                     # any NSE/BSE symbol e.g. "RELIANCE", "TCS.NS", "500325.BO"
    user_email: Optional[str] = None
    horizon_hint: Optional[str] = None   # "short_term" | "swing" | "long_term"


# ─── Pipeline orchestrator (runs in background) ────────────────────────────
async def _run_pipeline(run_id: str, symbol: str, user_email: Optional[str]) -> None:
    """Execute all 6 agents end-to-end, writing each step's output to
    `fund_runs.{run_id}` so the SSE stream can fetch updates by polling.
    Uses motor (async) so we never block the event loop, plus a sync pymongo
    client passed to the data tools that already expect a sync DB handle."""
    import pymongo
    sync_client = pymongo.MongoClient(os.environ["MONGO_URL"])
    sync_db = sync_client[os.environ["DB_NAME"]]
    motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = motor_client[os.environ["DB_NAME"]]
    sid = f"fund-{run_id}"

    async def _patch(stage: str, **fields):
        await db.fund_runs.update_one(
            {"run_id": run_id},
            {"$set": {f"stages.{stage}": fields, "current_stage": stage,
                      "updated_at": _now()},
             "$push": {"events": {"stage": stage, "ts": _now(), **fields}}},
        )

    try:
        # ── Step 0: gather data in parallel ──
        await _patch("data_gathering", status="running")
        fund_t = asyncio.to_thread(tools.fetch_fundamentals, symbol)
        tech_t = asyncio.to_thread(tools.fetch_technicals, symbol)
        sentiment_t = asyncio.to_thread(tools.fetch_sentiment, sync_db)
        news_t = asyncio.to_thread(tools.fetch_news, sync_db, symbol)
        portfolio_t = asyncio.to_thread(tools.fetch_portfolio_context, sync_db, user_email)
        compliance_t = tools.fetch_compliance_signal(symbol)

        fundamentals, technicals, sentiment, news_items, portfolio, compliance = await asyncio.gather(
            fund_t, tech_t, sentiment_t, news_t, portfolio_t, compliance_t,
        )
        await _patch("data_gathering", status="done",
                     fundamentals_ok=fundamentals.get("ok"),
                     technicals_ok=technicals.get("ok"),
                     sentiment_ok=sentiment.get("ok"),
                     news_count=len(news_items),
                     compliance_hits=compliance.get("n_hits", 0))

        # ── Step 1: 4 analysts in parallel ──
        await _patch("analysts", status="running")
        analyst_outputs = await asyncio.gather(
            agents.analyst_fundamentals(symbol, fundamentals, sid),
            agents.analyst_sentiment(symbol, sentiment, sid),
            agents.analyst_news(symbol, news_items, sid),
            agents.analyst_technical(symbol, technicals, sid),
            return_exceptions=True,
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
            agents.researcher_bull(symbol, analysts_dict, sid),
            agents.researcher_bear(symbol, analysts_dict, sid),
            return_exceptions=True,
        )
        debate = {"bull": _safe(bull), "bear": _safe(bear)}
        await _patch("debate", status="done", **debate)

        # ── Step 3: trader ──
        await _patch("trader", status="running")
        last_price = technicals.get("last_close")
        trade_proposal = await agents.trader(symbol, analysts_dict, debate, last_price, sid)
        await _patch("trader", status="done", **_safe(trade_proposal))

        # ── Step 4: risk manager ──
        await _patch("risk", status="running")
        risk_review = await agents.risk_manager(
            symbol, trade_proposal, portfolio, compliance, sid,
        )
        await _patch("risk", status="done", **_safe(risk_review))

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
        verdict = await agents.fund_manager(symbol, all_outputs, sid)
        await _patch("fund_manager", status="done", **_safe(verdict))

        await db.fund_runs.update_one(
            {"run_id": run_id},
            {"$set": {"final_verdict": _safe(verdict), "status": "completed",
                      "completed_at": _now()}},
        )
    except Exception as e:
        logger.exception(f"FUND pipeline {run_id} crashed")
        try:
            await db.fund_runs.update_one(
                {"run_id": run_id},
                {"$set": {"status": "error", "error": str(e)[:400]}},
            )
        except Exception:
            pass
    finally:
        sync_client.close()
        motor_client.close()


def _safe(x: Any) -> Dict:
    if isinstance(x, Exception):
        return {"error": str(x)[:200]}
    return x or {}


# ─── Endpoints ─────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    if not req.symbol or len(req.symbol.strip()) < 1:
        raise HTTPException(400, "symbol required")
    run_id = uuid.uuid4().hex[:16]
    db = request.app.db
    await db.fund_runs.insert_one({
        "run_id": run_id,
        "symbol": req.symbol.strip().upper(),
        "user_email": req.user_email,
        "horizon_hint": req.horizon_hint,
        "status": "running",
        "current_stage": "queued",
        "stages": {},
        "events": [],
        "created_at": _now(),
        "updated_at": _now(),
    })
    asyncio.create_task(_run_pipeline(run_id, req.symbol.strip().upper(), req.user_email))
    return {"run_id": run_id, "status": "running"}


@router.get("/stream/{run_id}")
async def stream(run_id: str, request: Request):
    """SSE stream of pipeline events. Client reconnects automatically via
    EventSource. Closes when status == completed/error."""
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
            if run.get("status") in ("completed", "error"):
                yield f"event: done\ndata: {json.dumps({'status': run.get('status'), 'final_verdict': run.get('final_verdict')}, default=str)}\n\n"
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

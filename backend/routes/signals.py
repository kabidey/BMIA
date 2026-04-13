"""Signal generation, evaluation, and tracking routes."""
import logging
import uuid
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.market_service import get_market_snapshot
from services.technical_service import full_technical_analysis
from services.fundamental_service import get_fundamentals
from services.news_service import fetch_news
from services.sentiment_service import analyze_sentiment
from services.alpha_service import full_alpha_computation
from services.intelligence_engine import generate_ai_signal
from services.signal_service import save_signal, get_active_signals, get_signal_history, evaluate_signal, evaluate_all_signals
from services.learning_service import build_learning_context, get_cached_learning_context
from services.performance_service import get_track_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["signals"])

_signal_jobs = {}


class GenerateSignalRequest(BaseModel):
    symbol: str
    provider: str = "openai"
    god_mode: bool = False


class EvaluateSignalRequest(BaseModel):
    signal_id: str
    current_price: Optional[float] = None


def _gather_raw_data(symbol):
    """Synchronous data gathering for signal generation."""
    raw_data = {}

    market_data = get_market_snapshot(symbol, "6mo", "1d")
    if "error" in market_data:
        return {"error": f"No market data for {symbol}"}

    raw_data["market_data"] = {
        "latest": market_data["latest"],
        "change": market_data["change"],
        "change_pct": market_data["change_pct"],
        "data_points": market_data["data_points"],
    }
    raw_data["chart_data"] = {"ohlcv": market_data["ohlcv"]}

    technical = full_technical_analysis(market_data["ohlcv"])
    raw_data["technical"] = technical

    fundamentals = get_fundamentals(symbol)
    raw_data["fundamental"] = fundamentals

    headlines = fetch_news(symbol)
    raw_data["news"] = {"headlines": headlines, "count": len(headlines)}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                sentiment = pool.submit(lambda: asyncio.run(analyze_sentiment(symbol, headlines))).result()
        else:
            sentiment = loop.run_until_complete(analyze_sentiment(symbol, headlines))
    except Exception:
        sentiment = {"sentiment_score_0_100": 50, "overall": "neutral"}
    raw_data["sentiment"] = sentiment

    tech_score = technical.get("technical_score", 50) if isinstance(technical, dict) else 50
    fund_score = fundamentals.get("fundamental_score", 50)
    sent_score = sentiment.get("sentiment_score_0_100", 50)
    alpha = full_alpha_computation(market_data["ohlcv"], tech_score, fund_score, sent_score)
    raw_data["alpha"] = alpha

    return raw_data


@router.post("/signals/generate")
async def generate_signal(req: GenerateSignalRequest, request: Request):
    symbol = req.symbol
    logger.info(f"Generating AI signal for {symbol}, god_mode={req.god_mode}")

    if req.god_mode:
        job_id = str(uuid.uuid4())[:8]
        _signal_jobs[job_id] = {"status": "running", "result": None, "error": None}

        async def _run_signal():
            try:
                raw_data = _gather_raw_data(symbol)
                if "error" in raw_data:
                    _signal_jobs[job_id]["status"] = "error"
                    _signal_jobs[job_id]["error"] = raw_data["error"]
                    return

                db = request.app.db
                learning_ctx = await get_cached_learning_context(db)

                from services.intelligence_engine import generate_god_mode_signal
                signal_data = await generate_god_mode_signal(symbol, raw_data, learning_ctx)

                if "error" in signal_data:
                    _signal_jobs[job_id]["status"] = "error"
                    _signal_jobs[job_id]["error"] = signal_data["error"]
                    return

                saved = await save_signal(db, signal_data, raw_data)
                try:
                    await build_learning_context(db)
                except Exception:
                    pass

                tech_score = raw_data.get("technical", {}).get("technical_score", 50)
                fund_score = raw_data.get("fundamental", {}).get("fundamental_score", 50)
                sent_score = raw_data.get("sentiment", {}).get("sentiment_score_0_100", 50)
                alpha_score = raw_data.get("alpha", {}).get("alpha_score", 50)

                _signal_jobs[job_id]["status"] = "complete"
                _signal_jobs[job_id]["result"] = {
                    "signal": saved,
                    "raw_scores": {
                        "technical_score": tech_score,
                        "fundamental_score": fund_score,
                        "sentiment_score": sent_score,
                        "alpha_score": alpha_score,
                    },
                    "learning_context_summary": {
                        "total_past_signals": learning_ctx.get("total_signals", 0),
                        "win_rate": learning_ctx.get("win_rate"),
                        "lessons_count": len(learning_ctx.get("lessons", [])),
                    },
                }
            except Exception as e:
                logger.error(f"God mode signal job {job_id} failed: {e}")
                _signal_jobs[job_id]["status"] = "error"
                _signal_jobs[job_id]["error"] = str(e)

        asyncio.create_task(_run_signal())
        return {"job_id": job_id, "status": "started", "async": True}

    raw_data = _gather_raw_data(symbol)
    if "error" in raw_data:
        raise HTTPException(status_code=404, detail=raw_data["error"])

    db = request.app.db
    learning_ctx = await get_cached_learning_context(db)

    signal_data = await generate_ai_signal(symbol, raw_data, learning_ctx, req.provider)
    if "error" in signal_data:
        raise HTTPException(status_code=500, detail=signal_data["error"])

    saved = await save_signal(db, signal_data, raw_data)
    try:
        await build_learning_context(db)
    except Exception:
        pass

    tech_score = raw_data.get("technical", {}).get("technical_score", 50) if isinstance(raw_data.get("technical"), dict) else 50
    fund_score = raw_data.get("fundamental", {}).get("fundamental_score", 50)
    sent_score = raw_data.get("sentiment", {}).get("sentiment_score_0_100", 50)
    alpha_score = raw_data.get("alpha", {}).get("alpha_score", 50)

    return {
        "signal": saved,
        "raw_scores": {
            "technical_score": tech_score,
            "fundamental_score": fund_score,
            "sentiment_score": sent_score,
            "alpha_score": alpha_score,
        },
        "learning_context_summary": {
            "total_past_signals": learning_ctx.get("total_signals", 0),
            "win_rate": learning_ctx.get("win_rate"),
            "lessons_count": len(learning_ctx.get("lessons", [])),
        },
    }


@router.get("/signals/generate-status/{job_id}")
async def signal_generate_status(job_id: str):
    job = _signal_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {"job_id": job_id, "status": job["status"]}

    if job["status"] == "complete" and job["result"]:
        response.update(job["result"])
        del _signal_jobs[job_id]
    elif job["status"] == "error":
        response["error"] = job.get("error", "Unknown error")
        del _signal_jobs[job_id]

    return response


import math


def _sanitize_float(val):
    """Replace NaN/Infinity with None for JSON safety."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _sanitize_dict(d):
    """Recursively sanitize NaN/Infinity in dicts/lists for JSON."""
    if isinstance(d, dict):
        return {k: _sanitize_dict(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_sanitize_dict(item) for item in d]
    if isinstance(d, float) and (math.isnan(d) or math.isinf(d)):
        return None
    return d


@router.get("/signals/active")
async def active_signals(request: Request, symbol: str = None):
    db = request.app.db
    signals = await get_active_signals(db, symbol)

    for sig in signals:
        if not sig.get("symbol"):
            continue
        try:
            market = get_market_snapshot(sig["symbol"], "5d", "1d")
            if "error" not in market:
                sig["current_price"] = market["latest"]["close"]
                entry_price = sig.get("entry_price", 0)
                if entry_price and entry_price > 0:
                    action = sig.get("action", "HOLD")
                    if action == "BUY":
                        sig["live_return_pct"] = round((market["latest"]["close"] - entry_price) / entry_price * 100, 2)
                    elif action == "SELL":
                        sig["live_return_pct"] = round((entry_price - market["latest"]["close"]) / entry_price * 100, 2)
                    else:
                        sig["live_return_pct"] = 0
        except Exception:
            pass

    return _sanitize_dict({"signals": signals, "total": len(signals)})


@router.get("/signals/history")
async def signal_history(request: Request, limit: int = 50, symbol: str = None, status: str = None):
    db = request.app.db
    signals = await get_signal_history(db, limit, symbol, status)
    return {"signals": signals, "total": len(signals)}


@router.post("/signals/evaluate")
async def evaluate_one_signal(req: EvaluateSignalRequest, request: Request):
    db = request.app.db

    current_price = req.current_price
    if not current_price:
        signal = await db.signals.find_one({"_id": __import__("bson").ObjectId(req.signal_id)})
        if signal:
            market = get_market_snapshot(signal["symbol"], "5d", "1d")
            if "error" not in market:
                current_price = market["latest"]["close"]

    if not current_price:
        raise HTTPException(status_code=400, detail="Could not determine current price")

    result = await evaluate_signal(db, req.signal_id, current_price)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/signals/evaluate-all")
async def evaluate_all(request: Request):
    db = request.app.db
    results = await evaluate_all_signals(db)
    await build_learning_context(db)
    return {"evaluated": len(results), "results": results}


@router.get("/signals/track-record")
async def track_record(request: Request):
    db = request.app.db
    return await get_track_record(db)


@router.get("/signals/learning-context")
async def learning_context(request: Request):
    db = request.app.db
    return await get_cached_learning_context(db)


@router.get("/signals/alerts")
async def signal_alerts(request: Request, since: Optional[str] = None):
    db = request.app.db
    query = {"status": {"$in": ["TARGET_HIT", "STOP_LOSS_HIT"]}}
    if since:
        query["evaluated_at"] = {"$gte": since}

    signals = await db.signals.find(query, {"_id": 0}).sort("evaluated_at", -1).limit(20).to_list(length=20)

    alerts = []
    for sig in signals:
        alert_type = "success" if sig.get("status") == "TARGET_HIT" else "danger"
        alerts.append({
            "symbol": sig.get("symbol", ""),
            "action": sig.get("action", ""),
            "status": sig.get("status", ""),
            "entry_price": sig.get("entry_price", 0),
            "current_price": sig.get("current_price", 0),
            "return_pct": sig.get("return_pct", 0),
            "alert_type": alert_type,
            "evaluated_at": sig.get("evaluated_at", ""),
        })

    return {"alerts": alerts}

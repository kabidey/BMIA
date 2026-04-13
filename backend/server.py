"""
Bharat Market Intel Agent (BMIA) - FastAPI Backend
"""
import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Optional, List
import numpy as np
import asyncio
import uuid

from symbols import NIFTY_50, MCX_COMMODITIES, ALL_SYMBOLS, SECTORS, get_symbol_info, search_symbols
from services.market_service import get_market_snapshot, get_ticker_info
from services.technical_service import full_technical_analysis
from services.fundamental_service import get_fundamentals
from services.news_service import fetch_news
from services.sentiment_service import analyze_sentiment
from services.alpha_service import full_alpha_computation
from services.ai_agent_service import get_ai_analysis
from services.intelligence_engine import generate_ai_signal, generate_batch_ranking
from services.signal_service import save_signal, get_active_signals, get_signal_history, evaluate_signal, evaluate_all_signals
from services.learning_service import build_learning_context, get_cached_learning_context
from services.performance_service import get_track_record
from services.dashboard_service import get_full_cockpit, get_slow_cockpit_modules, get_cached_cockpit, get_cached_cockpit_slow, start_background_cache
from services.full_market_scanner import god_mode_scan
from services.guidance_service import (
    get_guidance_items, get_guidance_stats, get_stock_list,
    run_full_scrape, start_guidance_scheduler,
)
from services.guidance_ai_service import ask_guidance_ai, get_suggested_questions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# In-memory job store for background god-scan tasks
_god_scan_jobs = {}
_signal_jobs = {}

# ── Background Evaluation Scheduler ──────────────────────────────────────────
def _start_evaluation_scheduler():
    """Daemon thread: auto-evaluates all open signals every 60 seconds."""
    import asyncio as _aio
    from motor.motor_asyncio import AsyncIOMotorClient as _MotorClient
    from services.signal_service import evaluate_all_signals
    from services.learning_service import build_learning_context
    import time as _t

    def _run():
        logger.info("EVAL SCHEDULER: Started (every 60s)")
        _t.sleep(30)  # initial delay — let app warm up
        while True:
            try:
                loop = _aio.new_event_loop()
                _aio.set_event_loop(loop)
                client = _MotorClient(MONGO_URL)
                db = client[DB_NAME]

                async def _eval():
                    results = await evaluate_all_signals(db)
                    evaluated = len(results)
                    if evaluated > 0:
                        logger.info(f"EVAL SCHEDULER: Evaluated {evaluated} signals")
                        try:
                            await build_learning_context(db)
                        except Exception:
                            pass
                    return evaluated

                loop.run_until_complete(_eval())
                client.close()
                loop.close()
            except Exception as e:
                logger.error(f"EVAL SCHEDULER error: {e}")
            _t.sleep(60)

    import threading
    t = threading.Thread(target=_run, daemon=True)
    t.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = AsyncIOMotorClient(MONGO_URL)
    app.db = app.mongodb_client[DB_NAME]
    logger.info("Connected to MongoDB")
    # Start background cockpit cache (non-blocking, daemon thread)
    try:
        start_background_cache()
    except Exception as e:
        logger.error(f"Background cache start failed (non-fatal): {e}")
    # Start auto-evaluation scheduler
    try:
        _start_evaluation_scheduler()
    except Exception as e:
        logger.error(f"Evaluation scheduler start failed (non-fatal): {e}")
    # Start guidance scraper (daily at 5 AM IST)
    try:
        start_guidance_scheduler(MONGO_URL, DB_NAME)
    except Exception as e:
        logger.error(f"Guidance scheduler start failed (non-fatal): {e}")
    yield
    app.mongodb_client.close()

app = FastAPI(title="Bharat Market Intel Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    symbol: str
    period: str = "6mo"
    interval: str = "1d"

class ChatRequest(BaseModel):
    symbol: str
    query: Optional[str] = None
    provider: str = "openai"
    analysis_data: Optional[dict] = None

class BatchRequest(BaseModel):
    symbols: Optional[List[str]] = None
    sector: Optional[str] = None

class BatchAIScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    sector: Optional[str] = None
    provider: str = "openai"

class GodScanRequest(BaseModel):
    market: str = "NSE"
    max_candidates: int = 80
    max_shortlist: int = 15
    top_n: int = 15

class GenerateSignalRequest(BaseModel):
    symbol: str
    provider: str = "openai"
    god_mode: bool = False

class EvaluateSignalRequest(BaseModel):
    signal_id: str
    current_price: Optional[float] = None


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "BMIA", "timestamp": datetime.now().isoformat()}


@app.get("/api/symbols")
async def list_symbols(q: str = Query(default="", description="Search query")):
    if q:
        results = search_symbols(q)
    else:
        results = ALL_SYMBOLS
    return {"symbols": results, "total": len(results)}


@app.get("/api/symbols/nifty50")
async def nifty50_symbols():
    return {"symbols": NIFTY_50}


@app.get("/api/symbols/commodities")
async def commodity_symbols():
    return {"symbols": MCX_COMMODITIES}


@app.get("/api/sectors")
async def list_sectors():
    return {"sectors": sorted(SECTORS)}


@app.get("/api/market/snapshot/{symbol}")
async def market_snapshot(symbol: str, period: str = "6mo", interval: str = "1d"):
    data = get_market_snapshot(symbol, period, interval)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@app.get("/api/market/info/{symbol}")
async def market_info(symbol: str):
    data = get_ticker_info(symbol)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@app.post("/api/analyze-stock")
async def analyze_stock(req: AnalyzeRequest):
    symbol = req.symbol
    logger.info(f"Analyzing {symbol}...")
    
    result = {"symbol": symbol, "timestamp": datetime.now().isoformat()}
    
    market_data = get_market_snapshot(symbol, req.period, req.interval)
    if "error" in market_data:
        result["market_data"] = {"error": market_data["error"]}
        result["technical"] = {"error": "No market data"}
        result["fundamental"] = get_fundamentals(symbol)
        result["news"] = {"headlines": fetch_news(symbol)}
        result["sentiment"] = {"score": 0, "sentiment_score_0_100": 50, "label": "Neutral"}
        result["alpha"] = full_alpha_computation([], 50, result["fundamental"].get("fundamental_score", 50), 50)
        return result
    
    result["market_data"] = {
        "latest": market_data["latest"],
        "change": market_data["change"],
        "change_pct": market_data["change_pct"],
        "data_points": market_data["data_points"],
    }
    
    technical = full_technical_analysis(market_data["ohlcv"])
    result["technical"] = technical
    
    fundamentals = get_fundamentals(symbol)
    result["fundamental"] = fundamentals
    
    headlines = fetch_news(symbol)
    result["news"] = {"headlines": headlines, "count": len(headlines)}
    
    sentiment = await analyze_sentiment(symbol, headlines)
    result["sentiment"] = sentiment
    
    tech_score = technical.get("technical_score", 50) if isinstance(technical, dict) else 50
    fund_score = fundamentals.get("fundamental_score", 50)
    sent_score = sentiment.get("sentiment_score_0_100", 50)
    
    alpha = full_alpha_computation(market_data["ohlcv"], tech_score, fund_score, sent_score)
    result["alpha"] = alpha
    
    info = get_symbol_info(symbol)
    result["symbol_info"] = info
    
    result["chart_data"] = {
        "ohlcv": market_data["ohlcv"],
        "rsi": technical.get("rsi", {}).get("chart", []) if isinstance(technical, dict) else [],
        "macd": technical.get("macd", {}).get("chart", []) if isinstance(technical, dict) else [],
    }
    
    try:
        db = app.db
        await db.analyses.insert_one({
            "symbol": symbol,
            "alpha_score": alpha["alpha_score"],
            "recommendation": alpha["recommendation"],
            "technical_score": tech_score,
            "fundamental_score": fund_score,
            "sentiment_score": sent_score,
            "timestamp": datetime.now(),
        })
    except Exception as e:
        logger.warning(f"MongoDB store error: {e}")
    
    return result


@app.post("/api/batch/analyze")
async def batch_analyze(req: BatchRequest):
    symbols = req.symbols
    if not symbols:
        if req.sector:
            symbols = [s["symbol"] for s in ALL_SYMBOLS if s["sector"] == req.sector]
        else:
            symbols = [s["symbol"] for s in NIFTY_50[:20]]
    
    results = []
    for sym in symbols:
        try:
            market_data = get_market_snapshot(sym, "6mo", "1d")
            if "error" in market_data:
                continue
            
            technical = full_technical_analysis(market_data["ohlcv"])
            fundamentals = get_fundamentals(sym)
            
            tech_score = technical.get("technical_score", 50) if isinstance(technical, dict) else 50
            fund_score = fundamentals.get("fundamental_score", 50)
            
            alpha_score = round(0.4 * tech_score + 0.4 * fund_score + 0.2 * 50, 2)
            
            from services.alpha_service import get_recommendation, get_recommendation_color
            
            info = get_symbol_info(sym)
            results.append({
                "symbol": sym,
                "name": info["name"],
                "sector": info["sector"],
                "price": market_data["latest"]["close"],
                "change": market_data["change"],
                "change_pct": market_data["change_pct"],
                "volume": market_data["latest"]["volume"],
                "rsi": technical.get("rsi", {}).get("current") if isinstance(technical, dict) else None,
                "technical_score": tech_score,
                "fundamental_score": fund_score,
                "alpha_score": alpha_score,
                "recommendation": get_recommendation(alpha_score),
                "recommendation_color": get_recommendation_color(get_recommendation(alpha_score)),
            })
        except Exception as e:
            logger.error(f"Batch error for {sym}: {e}")
    
    return {"results": results, "total": len(results)}


@app.post("/api/batch/ai-scan")
async def batch_ai_scan(req: BatchAIScanRequest):
    """AI-powered batch stock scanner with comprehensive ranking."""
    symbols = req.symbols
    if not symbols:
        if req.sector:
            symbols = [s["symbol"] for s in ALL_SYMBOLS if s["sector"] == req.sector]
        else:
            symbols = [s["symbol"] for s in NIFTY_50[:15]]

    # Cap at 15 stocks per batch for performance
    symbols = symbols[:15]

    # Gather expanded data for each symbol
    stocks_data = []
    for sym in symbols:
        try:
            market_data = get_market_snapshot(sym, "6mo", "1d")
            if "error" in market_data:
                continue

            technical = full_technical_analysis(market_data["ohlcv"])
            fundamentals = get_fundamentals(sym)

            info = get_symbol_info(sym)
            stocks_data.append({
                "symbol": sym,
                "name": info["name"],
                "sector": info["sector"],
                "market_data": {
                    "price": market_data["latest"]["close"],
                    "change": market_data["change"],
                    "change_pct": market_data["change_pct"],
                    "volume": market_data["latest"]["volume"],
                },
                "technical": technical if isinstance(technical, dict) else {},
                "fundamental": fundamentals if isinstance(fundamentals, dict) else {},
            })
        except Exception as e:
            logger.error(f"Batch AI data error for {sym}: {e}")

    if not stocks_data:
        return {"results": [], "total": 0, "ai_powered": True, "error": "No valid data found for symbols"}

    # Get AI ranking
    ranking_result = await generate_batch_ranking(stocks_data, req.provider)

    if "error" in ranking_result:
        # Fallback: return data without AI ranking
        fallback = []
        for sd in stocks_data:
            fallback.append({
                "symbol": sd["symbol"],
                "name": sd["name"],
                "sector": sd["sector"],
                "price": sd["market_data"]["price"],
                "change_pct": sd["market_data"]["change_pct"],
                "volume": sd["market_data"]["volume"],
                "rsi": sd["technical"].get("rsi", {}).get("current"),
                "ai_score": None,
                "action": "N/A",
                "conviction": "N/A",
                "rationale": f"AI ranking unavailable: {ranking_result['error']}",
                "key_strength": "N/A",
                "key_risk": "N/A",
                "rank": 0,
            })
        return {"results": fallback, "total": len(fallback), "ai_powered": False, "error": ranking_result["error"]}

    # Merge AI rankings with market data
    rankings = ranking_result.get("rankings", [])
    ranking_map = {r["symbol"]: r for r in rankings}

    results = []
    for sd in stocks_data:
        ai = ranking_map.get(sd["symbol"], {})
        results.append({
            "symbol": sd["symbol"],
            "name": sd["name"],
            "sector": sd["sector"],
            "price": sd["market_data"]["price"],
            "change": sd["market_data"]["change"],
            "change_pct": sd["market_data"]["change_pct"],
            "volume": sd["market_data"]["volume"],
            "rsi": sd["technical"].get("rsi", {}).get("current"),
            "macd_signal": sd["technical"].get("macd", {}).get("crossover"),
            "adx": sd["technical"].get("adx", {}).get("adx"),
            "adx_direction": sd["technical"].get("adx", {}).get("direction"),
            "bollinger_squeeze": sd["technical"].get("bollinger", {}).get("squeeze"),
            "obv_trend": sd["technical"].get("obv", {}).get("trend"),
            "pe_ratio": sd["fundamental"].get("pe_ratio"),
            "roe": sd["fundamental"].get("roe"),
            "revenue_growth": sd["fundamental"].get("revenue_growth"),
            # AI fields
            "rank": ai.get("rank", 99),
            "ai_score": ai.get("ai_score"),
            "action": ai.get("action", "N/A"),
            "conviction": ai.get("conviction", "N/A"),
            "rationale": ai.get("rationale", ""),
            "key_strength": ai.get("key_strength", ""),
            "key_risk": ai.get("key_risk", ""),
        })

    # Sort by AI rank
    results.sort(key=lambda x: x.get("rank", 99))

    return {
        "results": results,
        "total": len(results),
        "ai_powered": True,
        "provider": ranking_result.get("provider"),
        "model": ranking_result.get("model"),
        "generated_at": ranking_result.get("generated_at"),
    }


# ── In-memory cache for market overview & heatmap ─────────────────────
_overview_cache = {"data": None, "ts": 0}
_heatmap_cache = {"data": None, "ts": 0}
_OVERVIEW_TTL = 60  # seconds


def _refresh_overview():
    """Background-safe overview refresh."""
    from services.market_service import get_market_snapshot
    key_symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
                   "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LT.NS", "KOTAKBANK.NS",
                   "SUNPHARMA.NS", "WIPRO.NS", "BAJFINANCE.NS", "MARUTI.NS", "HCLTECH.NS"]
    movers = []
    for sym in key_symbols:
        try:
            data = get_market_snapshot(sym, "5d", "1d")
            if "error" not in data:
                info = get_symbol_info(sym)
                movers.append({
                    "symbol": sym,
                    "name": info["name"],
                    "sector": info["sector"],
                    "price": data["latest"]["close"],
                    "change": data["change"],
                    "change_pct": data["change_pct"],
                    "volume": data["latest"]["volume"],
                })
        except Exception as e:
            logger.error(f"Overview error for {sym}: {e}")
    movers.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    return {
        "gainers": movers[:5],
        "losers": movers[-5:][::-1] if len(movers) >= 5 else [],
        "all": movers,
        "timestamp": datetime.now().isoformat(),
    }


def _refresh_heatmap():
    """Background-safe heatmap refresh."""
    from services.market_service import get_market_snapshot
    heatmap = {}
    for sym_info in NIFTY_50[:30]:
        try:
            data = get_market_snapshot(sym_info["symbol"], "5d", "1d")
            if "error" not in data:
                sector = sym_info["sector"]
                if sector not in heatmap:
                    heatmap[sector] = []
                heatmap[sector].append({
                    "symbol": sym_info["symbol"],
                    "name": sym_info["name"],
                    "price": data["latest"]["close"],
                    "change_pct": data["change_pct"],
                    "volume": data["latest"]["volume"],
                })
        except Exception as e:
            logger.error(f"Heatmap error for {sym_info['symbol']}: {e}")
    return {"heatmap": heatmap, "timestamp": datetime.now().isoformat()}


def _bg_overview_heatmap_loop():
    """Daemon thread: refreshes overview & heatmap every 60s."""
    import time as _t
    while True:
        try:
            _overview_cache["data"] = _refresh_overview()
            _overview_cache["ts"] = _t.time()
            logger.info("BG CACHE: Market overview refreshed")
        except Exception as e:
            logger.error(f"BG CACHE overview error: {e}")
        try:
            _heatmap_cache["data"] = _refresh_heatmap()
            _heatmap_cache["ts"] = _t.time()
            logger.info("BG CACHE: Heatmap refreshed")
        except Exception as e:
            logger.error(f"BG CACHE heatmap error: {e}")
        _t.sleep(60)


import threading as _threading
_bg_thread_started = False


def _ensure_bg_threads():
    global _bg_thread_started
    if not _bg_thread_started:
        _bg_thread_started = True
        t = _threading.Thread(target=_bg_overview_heatmap_loop, daemon=True)
        t.start()
        logger.info("BG CACHE: Overview/heatmap background thread launched")


@app.get("/api/market/overview")
async def market_overview():
    _ensure_bg_threads()
    import time as _t
    if _overview_cache["data"] and (_t.time() - _overview_cache["ts"]) < _OVERVIEW_TTL:
        return _overview_cache["data"]
    # First call before cache warm
    data = _refresh_overview()
    _overview_cache["data"] = data
    _overview_cache["ts"] = _t.time()
    return data


@app.get("/api/market/heatmap")
async def market_heatmap():
    _ensure_bg_threads()
    import time as _t
    if _heatmap_cache["data"] and (_t.time() - _heatmap_cache["ts"]) < _OVERVIEW_TTL:
        return _heatmap_cache["data"]
    data = _refresh_heatmap()
    _heatmap_cache["data"] = data
    _heatmap_cache["ts"] = _t.time()
    return data


# ── Market Intelligence Cockpit Endpoints ─────────────────────────────────────
@app.get("/api/market/cockpit")
async def market_cockpit():
    """Consolidated dashboard data — returns pre-fetched cache instantly."""
    cached = get_cached_cockpit()
    if cached:
        return cached
    # Fallback: first request before cache is warm
    data = get_full_cockpit()
    return data


@app.get("/api/market/cockpit/slow")
async def market_cockpit_slow():
    """Slower modules — returns pre-fetched cache instantly."""
    cached = get_cached_cockpit_slow()
    if cached:
        return cached
    data = get_slow_cockpit_modules()
    return data


@app.post("/api/batch/god-scan")
async def batch_god_scan(req: GodScanRequest):
    """
    GOD MODE Full Market Scanner (Background Task):
    Starts scan in background, returns job_id for polling.
    """
    job_id = str(uuid.uuid4())[:8]
    logger.info(f"GOD SCAN job {job_id} initiated: market={req.market}, candidates={req.max_candidates}, shortlist={req.max_shortlist}")

    _god_scan_jobs[job_id] = {
        "status": "running",
        "stage": "universe",
        "progress": 0,
        "result": None,
        "error": None,
        "started_at": datetime.now().isoformat(),
    }

    async def _run_scan():
        try:
            # Update progress stages
            _god_scan_jobs[job_id]["stage"] = "universe"
            _god_scan_jobs[job_id]["progress"] = 10

            result = await god_mode_scan(
                market=req.market,
                max_candidates=req.max_candidates,
                max_shortlist=req.max_shortlist,
                top_n=req.top_n,
            )
            _god_scan_jobs[job_id]["status"] = "complete"
            _god_scan_jobs[job_id]["stage"] = "complete"
            _god_scan_jobs[job_id]["progress"] = 100
            _god_scan_jobs[job_id]["result"] = result
        except Exception as e:
            logger.error(f"GOD SCAN job {job_id} failed: {e}")
            _god_scan_jobs[job_id]["status"] = "error"
            _god_scan_jobs[job_id]["error"] = str(e)

    asyncio.create_task(_run_scan())
    return {"job_id": job_id, "status": "started"}


@app.get("/api/batch/god-scan/{job_id}")
async def batch_god_scan_status(job_id: str):
    """Poll god-scan job status."""
    job = _god_scan_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job_id,
        "status": job["status"],
        "stage": job.get("stage", "unknown"),
        "progress": job.get("progress", 0),
    }

    if job["status"] == "complete" and job["result"]:
        response.update(job["result"])
        # Clean up after serving results
        del _god_scan_jobs[job_id]
    elif job["status"] == "error":
        response["error"] = job.get("error", "Unknown error")
        del _god_scan_jobs[job_id]

    return response


@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest):
    analysis_data = req.analysis_data or {}
    
    if not analysis_data:
        market_data = get_market_snapshot(req.symbol, "6mo", "1d")
        if "error" not in market_data:
            technical = full_technical_analysis(market_data["ohlcv"])
            fundamentals = get_fundamentals(req.symbol)
            analysis_data = {
                "market": {"price": market_data["latest"]["close"], "change_pct": market_data["change_pct"]},
                "technical": {"score": technical.get("technical_score", 50), "rsi": technical.get("rsi", {}).get("current")},
                "fundamental": fundamentals,
            }
    
    result = await get_ai_analysis(req.symbol, analysis_data, req.query, req.provider)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/api/analyses/history")
async def analysis_history(limit: int = 20):
    try:
        db = app.db
        cursor = db.analyses.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        # Serialize datetime objects
        for r in results:
            if "timestamp" in r and hasattr(r["timestamp"], "isoformat"):
                r["timestamp"] = r["timestamp"].isoformat()
        return {"history": results}
    except Exception as e:
        return {"history": [], "error": str(e)}


# ========== SIGNAL ENDPOINTS ==========

@app.post("/api/signals/generate")
async def generate_signal(req: GenerateSignalRequest):
    """Generate an AI-driven trade signal. God Mode runs as background task with polling."""
    symbol = req.symbol
    logger.info(f"Generating AI signal for {symbol}, god_mode={req.god_mode}")

    if req.god_mode:
        # Background task pattern for God Mode (prevents proxy timeout)
        job_id = str(uuid.uuid4())[:8]
        _signal_jobs[job_id] = {"status": "running", "result": None, "error": None}

        async def _run_signal():
            try:
                raw_data = _gather_raw_data(symbol)
                if "error" in raw_data:
                    _signal_jobs[job_id]["status"] = "error"
                    _signal_jobs[job_id]["error"] = raw_data["error"]
                    return

                db = app.db
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

    # Non-God Mode: synchronous (fast enough)
    raw_data = _gather_raw_data(symbol)
    if "error" in raw_data:
        raise HTTPException(status_code=404, detail=raw_data["error"])

    db = app.db
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

    # Sentiment is async - handle in sync context
    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                sentiment = pool.submit(lambda: _asyncio.run(analyze_sentiment(symbol, headlines))).result()
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


@app.get("/api/signals/generate-status/{job_id}")
async def signal_generate_status(job_id: str):
    """Poll signal generation job status."""
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


@app.get("/api/signals/active")
async def active_signals(symbol: str = None):
    """Get all active (open) signals."""
    db = app.db
    signals = await get_active_signals(db, symbol)

    # Update current prices for live P&L
    for sig in signals:
        try:
            market = get_market_snapshot(sig["symbol"], "5d", "1d")
            if "error" not in market:
                sig["current_price"] = market["latest"]["close"]
                entry_price = sig.get("entry_price", 0)
                if entry_price > 0:
                    action = sig.get("action", "HOLD")
                    if action == "BUY":
                        sig["live_return_pct"] = round((market["latest"]["close"] - entry_price) / entry_price * 100, 2)
                    elif action == "SELL":
                        sig["live_return_pct"] = round((entry_price - market["latest"]["close"]) / entry_price * 100, 2)
                    else:
                        sig["live_return_pct"] = 0
        except Exception:
            pass

    return {"signals": signals, "total": len(signals)}


@app.get("/api/signals/history")
async def signal_history(limit: int = 50, symbol: str = None, status: str = None):
    """Get signal history with filters."""
    db = app.db
    signals = await get_signal_history(db, limit, symbol, status)
    return {"signals": signals, "total": len(signals)}


@app.post("/api/signals/evaluate")
async def evaluate_one_signal(req: EvaluateSignalRequest):
    """Evaluate a single signal."""
    db = app.db

    current_price = req.current_price
    if not current_price:
        # Fetch current price
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


@app.post("/api/signals/evaluate-all")
async def evaluate_all():
    """Evaluate all open signals against current prices."""
    db = app.db
    results = await evaluate_all_signals(db)
    # Refresh learning context after evaluation
    await build_learning_context(db)
    return {"evaluated": len(results), "results": results}


@app.get("/api/signals/track-record")
async def track_record():
    """Get comprehensive track record metrics."""
    db = app.db
    return await get_track_record(db)


@app.get("/api/signals/learning-context")
async def learning_context():
    """Get current learning context (what the AI has learned)."""
    db = app.db
    return await get_cached_learning_context(db)


# ═══════════════════════════════════════════════════════════════════════════════
# GUIDANCE — BSE Corporate Announcements & Filings
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/guidance")
async def guidance_items(
    symbol: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """Get guidance items with filters and pagination."""
    db = app.db
    return await get_guidance_items(db, symbol=symbol, category=category, search=search, page=page, limit=limit)


@app.get("/api/guidance/stats")
async def guidance_stats():
    """Get guidance dashboard stats."""
    db = app.db
    return await get_guidance_stats(db)


@app.get("/api/guidance/stocks")
async def guidance_stocks():
    """Get all stocks that have guidance data."""
    db = app.db
    stocks = await get_stock_list(db)
    return {"stocks": stocks, "total": len(stocks)}


@app.post("/api/guidance/scrape")
async def trigger_guidance_scrape(days_back: int = 7):
    """Manually trigger a guidance scrape (background task)."""
    db = app.db
    job_id = str(uuid.uuid4())[:8]
    _god_scan_jobs[job_id] = {"status": "running", "result": None, "error": None}

    async def _run():
        try:
            result = await run_full_scrape(db, days_back=days_back)
            _god_scan_jobs[job_id]["status"] = "complete"
            _god_scan_jobs[job_id]["result"] = result
        except Exception as e:
            _god_scan_jobs[job_id]["status"] = "error"
            _god_scan_jobs[job_id]["error"] = str(e)

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "started"}


@app.get("/api/guidance/scrape/{job_id}")
async def guidance_scrape_status(job_id: str):
    """Poll guidance scrape job status."""
    job = _god_scan_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "complete" and job["result"]:
        response.update(job["result"])
        del _god_scan_jobs[job_id]
    elif job["status"] == "error":
        response["error"] = job.get("error")
        del _god_scan_jobs[job_id]
    return response


# ── Guidance AI (RAG) Endpoints ───────────────────────────────────────────────

class GuidanceAskRequest(BaseModel):
    question: str
    conversation_history: Optional[list] = None


@app.post("/api/guidance/ask")
async def guidance_ask(req: GuidanceAskRequest):
    """Ask an AI-powered question about BSE corporate filings."""
    db = app.db
    result = await ask_guidance_ai(db, req.question, req.conversation_history)
    return result


@app.get("/api/guidance/suggestions")
async def guidance_suggestions():
    """Get AI-generated suggested questions based on current filings."""
    db = app.db
    suggestions = await get_suggested_questions(db)
    return {"suggestions": suggestions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

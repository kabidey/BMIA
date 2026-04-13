"""Analysis & batch scanning routes."""
import logging
import uuid
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from symbols import ALL_SYMBOLS, NIFTY_50, get_symbol_info
from services.market_service import get_market_snapshot
from services.technical_service import full_technical_analysis
from services.fundamental_service import get_fundamentals
from services.news_service import fetch_news
from services.sentiment_service import analyze_sentiment
from services.alpha_service import full_alpha_computation
from services.ai_agent_service import get_ai_analysis
from services.intelligence_engine import generate_batch_ranking
from services.full_market_scanner import god_mode_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])

# In-memory job store for background god-scan tasks
_god_scan_jobs = {}


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


@router.post("/analyze-stock")
async def analyze_stock(req: AnalyzeRequest, request: Request):
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
        db = request.app.db
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


@router.post("/batch/analyze")
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


@router.post("/batch/ai-scan")
async def batch_ai_scan(req: BatchAIScanRequest):
    symbols = req.symbols
    if not symbols:
        if req.sector:
            symbols = [s["symbol"] for s in ALL_SYMBOLS if s["sector"] == req.sector]
        else:
            symbols = [s["symbol"] for s in NIFTY_50[:15]]

    symbols = symbols[:15]

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

    ranking_result = await generate_batch_ranking(stocks_data, req.provider)

    if "error" in ranking_result:
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
            "rank": ai.get("rank", 99),
            "ai_score": ai.get("ai_score"),
            "action": ai.get("action", "N/A"),
            "conviction": ai.get("conviction", "N/A"),
            "rationale": ai.get("rationale", ""),
            "key_strength": ai.get("key_strength", ""),
            "key_risk": ai.get("key_risk", ""),
        })

    results.sort(key=lambda x: x.get("rank", 99))

    return {
        "results": results,
        "total": len(results),
        "ai_powered": True,
        "provider": ranking_result.get("provider"),
        "model": ranking_result.get("model"),
        "generated_at": ranking_result.get("generated_at"),
    }


@router.post("/batch/god-scan")
async def batch_god_scan(req: GodScanRequest, request: Request):
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

    db = request.app.db

    async def _run_scan():
        try:
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

            # Save to scanner history
            try:
                history_doc = {
                    "scan_id": job_id,
                    "scanned_at": datetime.now().isoformat(),
                    "god_mode": result.get("god_mode", False),
                    "models_succeeded": result.get("models_succeeded", []),
                    "pipeline": result.get("pipeline", {}),
                    "total_results": result.get("total", 0),
                    "results_summary": [
                        {
                            "symbol": r.get("symbol", ""),
                            "name": r.get("name", ""),
                            "sector": r.get("sector", ""),
                            "price": r.get("price", 0),
                            "change_pct": r.get("change_pct", 0),
                            "ai_score": r.get("ai_score"),
                            "action": r.get("action", "N/A"),
                            "agreement_level": r.get("agreement_level", "N/A"),
                            "rank": r.get("rank", 99),
                            "factor_score": r.get("factor_score"),
                            "rationale": (r.get("rationale", "") or "")[:200],
                        }
                        for r in (result.get("results", []) or [])
                    ],
                }
                await db.scanner_history.insert_one(history_doc)
                logger.info(f"GOD SCAN history saved: {job_id}")
            except Exception as he:
                logger.error(f"Failed to save scan history: {he}")

        except Exception as e:
            logger.error(f"GOD SCAN job {job_id} failed: {e}")
            _god_scan_jobs[job_id]["status"] = "error"
            _god_scan_jobs[job_id]["error"] = str(e)

    asyncio.create_task(_run_scan())
    return {"job_id": job_id, "status": "started"}


@router.get("/batch/god-scan/{job_id}")
async def batch_god_scan_status(job_id: str):
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
        del _god_scan_jobs[job_id]
    elif job["status"] == "error":
        response["error"] = job.get("error", "Unknown error")
        del _god_scan_jobs[job_id]

    return response


@router.get("/batch/scan-history")
async def scan_history(request: Request, limit: int = 20):
    """Get history of past God Mode scans."""
    db = request.app.db
    cursor = db.scanner_history.find({}, {"_id": 0}).sort("scanned_at", -1).limit(limit)
    history = await cursor.to_list(length=limit)
    return {"scans": history, "total": len(history)}


@router.post("/ai/chat")
async def ai_chat(req: ChatRequest, request: Request):
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


@router.get("/analyses/history")
async def analysis_history(request: Request, limit: int = 20):
    try:
        db = request.app.db
        cursor = db.analyses.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        for r in results:
            if "timestamp" in r and hasattr(r["timestamp"], "isoformat"):
                r["timestamp"] = r["timestamp"].isoformat()
        return {"history": results}
    except Exception as e:
        return {"history": [], "error": str(e)}

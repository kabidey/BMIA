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

from symbols import NIFTY_50, MCX_COMMODITIES, ALL_SYMBOLS, SECTORS, get_symbol_info, search_symbols
from services.market_service import get_market_snapshot, get_ticker_info
from services.technical_service import full_technical_analysis
from services.fundamental_service import get_fundamentals
from services.news_service import fetch_news
from services.sentiment_service import analyze_sentiment
from services.alpha_service import full_alpha_computation
from services.ai_agent_service import get_ai_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "bmia_db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = AsyncIOMotorClient(MONGO_URL)
    app.db = app.mongodb_client[DB_NAME]
    logger.info("Connected to MongoDB")
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


@app.get("/api/market/overview")
async def market_overview():
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


@app.get("/api/market/heatmap")
async def market_heatmap():
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

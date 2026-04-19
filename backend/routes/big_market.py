"""Big Market — Koyfin-style global market dashboard routes."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

from services.big_market_service import fetch_all_market_data, fetch_stock_snapshot
from services.market_intel import (
    get_market_news,
    get_analyst_estimates,
    get_earnings_calendar,
    get_pcr_history,
    get_market_movers_scatter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["big-market"])


@router.get("/big-market/overview")
async def big_market_overview():
    data = await asyncio.get_event_loop().run_in_executor(None, fetch_all_market_data)
    return data


@router.get("/big-market/snapshot/{symbol}")
async def stock_snapshot(symbol: str):
    data = await asyncio.get_event_loop().run_in_executor(None, fetch_stock_snapshot, symbol)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return data


# ── New modules ───────────────────────────────────────────────────────────────
@router.get("/big-market/movers")
async def big_market_movers():
    """Gainers / losers / high-volume formatted for scatter visualization."""
    return await asyncio.get_event_loop().run_in_executor(None, get_market_movers_scatter)


@router.get("/big-market/fii-dii")
async def big_market_fii_dii():
    """Institutional flows — FII + DII net cash + F&O flows."""
    from services.dashboard_service import get_fii_dii_flows
    return await asyncio.get_event_loop().run_in_executor(None, get_fii_dii_flows) or {}


@router.get("/big-market/earnings-calendar")
async def big_market_earnings(request: Request, days: int = 14):
    """Upcoming board meetings, earnings, dividends from NSE+BSE feeds."""
    days = max(1, min(days, 60))
    return await get_earnings_calendar(request.app.db, days=days)


@router.get("/big-market/pcr")
async def big_market_pcr(request: Request, days: int = 30):
    """Put-Call Ratio — Nifty + BankNifty current + history."""
    return await asyncio.get_event_loop().run_in_executor(None, get_pcr_history, request.app.db, days)


@router.get("/big-market/analyst-estimates/{symbol}")
async def big_market_analyst_estimates(symbol: str):
    """Consensus analyst estimates for a stock — EPS, target, rating mix."""
    data = await asyncio.get_event_loop().run_in_executor(None, get_analyst_estimates, symbol)
    return data or {"symbol": symbol.upper()}


@router.get("/big-market/news")
async def big_market_news(limit: int = 25):
    """Curated market news from our aggregators."""
    limit = max(5, min(limit, 100))
    return await asyncio.get_event_loop().run_in_executor(None, get_market_news, limit)


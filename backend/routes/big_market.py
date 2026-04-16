"""Big Market — Koyfin-style global market dashboard routes."""
import logging
from fastapi import APIRouter, HTTPException, Request

from services.big_market_service import fetch_all_market_data, fetch_stock_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["big-market"])


@router.get("/big-market/overview")
async def big_market_overview():
    """Get full market overview — indices, sectors, commodities, currencies, yields, factor grid."""
    import asyncio
    data = await asyncio.get_event_loop().run_in_executor(None, fetch_all_market_data)
    return data


@router.get("/big-market/snapshot/{symbol}")
async def stock_snapshot(symbol: str):
    """Get Koyfin-style stock snapshot for a single security."""
    import asyncio
    data = await asyncio.get_event_loop().run_in_executor(None, fetch_stock_snapshot, symbol)
    if not data:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return data

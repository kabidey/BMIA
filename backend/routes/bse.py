"""BSE price data routes."""
from fastapi import APIRouter, HTTPException

from services.bse_price_service import (
    get_bse_quote, get_bse_gainers, get_bse_losers,
    get_bse_near_52w, get_bse_advance_decline,
)

router = APIRouter(prefix="/api", tags=["bse"])


@router.get("/bse/quote/{scrip_code}")
async def bse_quote(scrip_code: str):
    data = get_bse_quote(scrip_code)
    if not data:
        raise HTTPException(status_code=404, detail="Quote not found")
    return data


@router.get("/bse/gainers")
async def bse_gainers():
    return {"gainers": get_bse_gainers()}


@router.get("/bse/losers")
async def bse_losers():
    return {"losers": get_bse_losers()}


@router.get("/bse/near-52w/{direction}")
async def bse_near_52w(direction: str):
    if direction not in ("high", "low"):
        raise HTTPException(status_code=400, detail="direction must be 'high' or 'low'")
    return {"stocks": get_bse_near_52w(direction)}


@router.get("/bse/advance-decline")
async def bse_advance_decline():
    return get_bse_advance_decline()

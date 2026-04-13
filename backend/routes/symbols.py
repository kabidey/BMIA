"""Symbol & sector lookup routes."""
from fastapi import APIRouter, Query

from symbols import NIFTY_50, MCX_COMMODITIES, ALL_SYMBOLS, SECTORS, search_symbols

router = APIRouter(prefix="/api", tags=["symbols"])


@router.get("/symbols")
async def list_symbols(q: str = Query(default="", description="Search query")):
    if q:
        results = search_symbols(q)
    else:
        results = ALL_SYMBOLS
    return {"symbols": results, "total": len(results)}


@router.get("/symbols/nifty50")
async def nifty50_symbols():
    return {"symbols": NIFTY_50}


@router.get("/symbols/commodities")
async def commodity_symbols():
    return {"symbols": MCX_COMMODITIES}


@router.get("/sectors")
async def list_sectors():
    return {"sectors": sorted(SECTORS)}

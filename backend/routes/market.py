"""Market data routes — cockpit, overview, heatmap, snapshots."""
from fastapi import APIRouter, HTTPException, Request

from services.market_service import get_market_snapshot, get_ticker_info
from services.dashboard_service import get_full_cockpit, get_slow_cockpit_modules, get_cached_cockpit, get_cached_cockpit_slow
from daemons.market_cache import (
    ensure_bg_threads, get_cached_overview, set_overview_cache,
    get_cached_heatmap, set_heatmap_cache, _refresh_overview, _refresh_heatmap,
)

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/market/snapshot/{symbol}")
async def market_snapshot(symbol: str, period: str = "6mo", interval: str = "1d"):
    data = get_market_snapshot(symbol, period, interval)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/market/info/{symbol}")
async def market_info(symbol: str):
    data = get_ticker_info(symbol)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/market/overview")
async def market_overview():
    ensure_bg_threads()
    cached = get_cached_overview()
    if cached:
        return cached
    data = _refresh_overview()
    set_overview_cache(data)
    return data


@router.get("/market/heatmap")
async def market_heatmap():
    ensure_bg_threads()
    cached = get_cached_heatmap()
    if cached:
        return cached
    data = _refresh_heatmap()
    set_heatmap_cache(data)
    return data


@router.get("/market/cockpit")
async def market_cockpit():
    cached = get_cached_cockpit()
    if cached:
        return cached
    data = get_full_cockpit()
    return data


@router.get("/market/cockpit/slow")
async def market_cockpit_slow():
    cached = get_cached_cockpit_slow()
    if cached:
        return cached
    data = get_slow_cockpit_modules()
    return data

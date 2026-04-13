"""Autonomous portfolio routes."""
from fastapi import APIRouter, HTTPException, Request

from services.portfolio_engine import (
    get_all_portfolios, get_portfolio, get_rebalance_log,
    get_portfolio_overview, construct_portfolio, update_portfolio_prices,
    PORTFOLIO_STRATEGIES,
)

router = APIRouter(prefix="/api", tags=["portfolios"])


@router.get("/portfolios/overview")
async def portfolio_overview(request: Request):
    db = request.app.db
    return await get_portfolio_overview(db)


@router.get("/portfolios/rebalance-log-all/recent")
async def all_rebalance_logs(request: Request, limit: int = 30):
    db = request.app.db
    logs = await get_rebalance_log(db, limit=limit)
    return {"logs": logs}


@router.get("/portfolios/rebalance-log/{strategy_type}")
async def portfolio_rebalance_log(strategy_type: str, request: Request, limit: int = 20):
    db = request.app.db
    logs = await get_rebalance_log(db, strategy_type, limit)
    return {"logs": logs}


@router.get("/portfolios/{strategy_type}")
async def portfolio_detail(strategy_type: str, request: Request):
    db = request.app.db
    p = await get_portfolio(db, strategy_type)
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return p


@router.post("/portfolios/{strategy_type}/refresh-prices")
async def portfolio_refresh_prices(strategy_type: str, request: Request):
    db = request.app.db
    result = await update_portfolio_prices(db, strategy_type)
    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found or not active")
    return result


@router.post("/portfolios/{strategy_type}/construct")
async def portfolio_construct(strategy_type: str, request: Request):
    db = request.app.db
    if strategy_type not in PORTFOLIO_STRATEGIES:
        raise HTTPException(status_code=400, detail="Invalid strategy type")
    result = await construct_portfolio(db, strategy_type)
    return result


@router.get("/portfolios")
async def portfolios_list(request: Request):
    db = request.app.db
    portfolios = await get_all_portfolios(db)
    return {"portfolios": portfolios, "strategies": PORTFOLIO_STRATEGIES}

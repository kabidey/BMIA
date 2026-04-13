"""Autonomous portfolio routes."""
import math
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request

from services.portfolio_engine import (
    get_all_portfolios, get_portfolio, get_rebalance_log,
    get_portfolio_overview, construct_portfolio, update_portfolio_prices,
    PORTFOLIO_STRATEGIES, INITIAL_CAPITAL,
)

router = APIRouter(prefix="/api", tags=["portfolios"])


@router.get("/portfolios/overview")
async def portfolio_overview(request: Request):
    db = request.app.db
    return await get_portfolio_overview(db)


@router.get("/portfolios/analytics")
async def portfolio_analytics(request: Request):
    """Portfolio analytics: sector allocation, risk metrics, performance comparison."""
    db = request.app.db
    portfolios = await get_all_portfolios(db)
    active = [p for p in portfolios if p.get("status") == "active"]

    if not active:
        return {"error": "No active portfolios", "portfolios": []}

    # Global sector allocation across all portfolios
    global_sectors = defaultdict(float)
    global_invested = 0

    portfolio_analytics = []
    for p in active:
        holdings = p.get("holdings", [])
        if not holdings:
            continue

        ptype = p.get("type", "")
        invested = p.get("actual_invested", INITIAL_CAPITAL)
        current_val = p.get("current_value", invested)
        pnl = p.get("total_pnl", 0)
        pnl_pct = p.get("total_pnl_pct", 0)

        # Sector allocation for this portfolio
        sector_alloc = defaultdict(float)
        betas = []
        pnl_values = []
        stock_count = len(holdings)
        winners = 0
        losers = 0

        for h in holdings:
            sector = h.get("sector", "Other") or "Other"
            alloc = h.get("allocation", 0)
            sector_alloc[sector] += alloc
            global_sectors[sector] += alloc
            global_invested += alloc

            hp = h.get("pnl_pct", 0) or 0
            pnl_values.append(hp)
            if hp > 0:
                winners += 1
            elif hp < 0:
                losers += 1

            beta = h.get("beta")
            if beta and isinstance(beta, (int, float)) and not math.isnan(beta):
                betas.append(beta)

        # Risk metrics
        avg_beta = round(sum(betas) / len(betas), 2) if betas else None
        volatility = round(
            (sum((x - (sum(pnl_values)/len(pnl_values)))**2 for x in pnl_values) / len(pnl_values))**0.5, 2
        ) if pnl_values else 0

        # Win rate
        win_rate = round(winners / stock_count * 100, 1) if stock_count else 0

        # Max gain / max loss
        max_gain = round(max(pnl_values), 2) if pnl_values else 0
        max_loss = round(min(pnl_values), 2) if pnl_values else 0

        # Top/bottom performers
        sorted_holdings = sorted(holdings, key=lambda x: x.get("pnl_pct", 0) or 0, reverse=True)
        top_performer = sorted_holdings[0] if sorted_holdings else None
        worst_performer = sorted_holdings[-1] if sorted_holdings else None

        # Concentration: weight of top 3 holdings
        top3_weight = round(sum(h.get("weight", 0) for h in sorted(holdings, key=lambda x: x.get("weight", 0), reverse=True)[:3]), 1)

        sector_list = [{"sector": s, "value": round(v, 2), "pct": round(v / invested * 100, 1) if invested else 0} for s, v in sorted(sector_alloc.items(), key=lambda x: x[1], reverse=True)]

        portfolio_analytics.append({
            "type": ptype,
            "name": p.get("name", ""),
            "invested": round(invested, 2),
            "current_value": round(current_val, 2),
            "total_pnl": round(pnl, 2),
            "total_pnl_pct": round(pnl_pct, 2),
            "holdings_count": stock_count,
            "winners": winners,
            "losers": losers,
            "win_rate": win_rate,
            "avg_beta": avg_beta,
            "volatility": volatility,
            "max_gain_pct": max_gain,
            "max_loss_pct": max_loss,
            "top3_concentration": top3_weight,
            "sector_allocation": sector_list,
            "top_performer": {
                "symbol": top_performer.get("symbol", "").replace(".NS", ""),
                "pnl_pct": round(top_performer.get("pnl_pct", 0) or 0, 2),
            } if top_performer else None,
            "worst_performer": {
                "symbol": worst_performer.get("symbol", "").replace(".NS", ""),
                "pnl_pct": round(worst_performer.get("pnl_pct", 0) or 0, 2),
            } if worst_performer else None,
            "horizon": p.get("horizon", ""),
            "created_at": p.get("created_at"),
            "last_rebalanced": p.get("last_rebalanced"),
            "pipeline": p.get("construction_log", {}).get("pipeline", "v1"),
        })

    # Global sector allocation
    global_sector_list = [
        {"sector": s, "value": round(v, 2), "pct": round(v / global_invested * 100, 1) if global_invested else 0}
        for s, v in sorted(global_sectors.items(), key=lambda x: x[1], reverse=True)
    ]

    # Aggregate risk
    all_betas = [pa["avg_beta"] for pa in portfolio_analytics if pa["avg_beta"] is not None]
    aggregate_beta = round(sum(all_betas) / len(all_betas), 2) if all_betas else None
    total_invested = sum(pa["invested"] for pa in portfolio_analytics)
    total_value = sum(pa["current_value"] for pa in portfolio_analytics)
    total_pnl = round(total_value - total_invested, 2)
    total_pnl_pct = round(total_pnl / total_invested * 100, 2) if total_invested else 0

    return {
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "aggregate_beta": aggregate_beta,
        "active_count": len(active),
        "global_sector_allocation": global_sector_list,
        "portfolios": portfolio_analytics,
    }


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

"""Autonomous portfolio routes."""
import math
import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request

from services.portfolio_engine import (
    get_all_portfolios, get_portfolio, get_rebalance_log,
    get_portfolio_overview, construct_portfolio, update_portfolio_prices,
    PORTFOLIO_STRATEGIES, INITIAL_CAPITAL,
)

router = APIRouter(prefix="/api", tags=["portfolios"])

# Track in-progress background simulations
_simulation_locks = {}  # strategy_type -> bool


@router.get("/portfolios/overview")
async def portfolio_overview(request: Request):
    db = request.app.db
    # Auto-clean stuck "constructing" portfolios (>10 min old)
    from datetime import timedelta
    stuck = await db.portfolios.find({"status": "constructing"}).to_list(length=20)
    for s in stuck:
        created = s.get("constructed_at") or s.get("created_at")
        if created and isinstance(created, datetime):
            if (datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)).total_seconds() > 600:
                await db.portfolios.delete_one({"_id": s["_id"]})
        else:
            # No timestamp — just delete it, it's stale
            await db.portfolios.delete_one({"_id": s["_id"]})
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
        capital = p.get("initial_capital", INITIAL_CAPITAL)
        invested = p.get("actual_invested", capital)
        current_val = p.get("current_value", invested)
        # P&L vs committed capital (honest), not vs shrunken invested
        pnl = current_val - capital
        pnl_pct = (pnl / capital * 100) if capital else 0

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
            "capital": round(capital, 2),
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
    total_capital = sum(pa["capital"] for pa in portfolio_analytics)
    total_invested = sum(pa["invested"] for pa in portfolio_analytics)
    total_value = sum(pa["current_value"] for pa in portfolio_analytics)
    # Aggregate P&L vs committed capital
    total_pnl = round(total_value - total_capital, 2)
    total_pnl_pct = round(total_pnl / total_capital * 100, 2) if total_capital else 0

    return {
        "total_capital": round(total_capital, 2),
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


_backtest_locks = {}  # strategy_type -> bool


@router.get("/portfolios/backtest/{strategy_type}")
async def portfolio_backtest(strategy_type: str, request: Request):
    """Run 5-year lookback backtest for a portfolio's holdings vs Nifty 50.
    Returns cached result or triggers background computation."""
    from services.portfolio_hardening import compute_backtest
    import logging
    logger = logging.getLogger(__name__)

    db = request.app.db
    portfolio = await get_portfolio(db, strategy_type)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Check cache (24h TTL)
    cached = await db.portfolio_backtests.find_one(
        {"portfolio_type": strategy_type}, {"_id": 0}
    )
    if cached:
        cached_at = cached.get("computed_at", "")
        try:
            ct = datetime.fromisoformat(cached_at)
            if (datetime.now(timezone.utc) - ct.replace(tzinfo=timezone.utc)).total_seconds() < 86400:
                cached["status"] = "complete"
                return cached
        except Exception:
            pass

    # If already computing, return status
    if _backtest_locks.get(strategy_type):
        return {"status": "computing", "portfolio_type": strategy_type,
                "message": f"Backtest computation in progress for {strategy_type}..."}

    symbols = [h["symbol"] for h in portfolio.get("holdings", []) if h.get("symbol")]
    strategy_name = portfolio.get("name", strategy_type)

    import os
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    def _run_backtest_bg():
        import pymongo
        try:
            _backtest_locks[strategy_type] = True
            result = compute_backtest(symbols, strategy_name)
            result["portfolio_type"] = strategy_type
            result["computed_at"] = datetime.now(timezone.utc).isoformat()
            result["status"] = "complete"

            client = pymongo.MongoClient(mongo_url)
            sync_db = client[db_name]
            sync_db.portfolio_backtests.update_one(
                {"portfolio_type": strategy_type},
                {"$set": result},
                upsert=True,
            )
            client.close()
            logger.info(f"Backtest stored for {strategy_type}")
        except Exception as e:
            logger.error(f"Background backtest error for {strategy_type}: {e}")
        finally:
            _backtest_locks[strategy_type] = False

    thread = threading.Thread(target=_run_backtest_bg, daemon=True)
    thread.start()

    return {"status": "computing", "portfolio_type": strategy_type,
            "message": f"Backtest started for {strategy_type}. Poll again in ~30s."}


@router.get("/portfolios/simulation/{strategy_type}")
async def portfolio_simulation(strategy_type: str, request: Request):
    """Run LSTM + Monte Carlo forward simulation for a portfolio.
    Returns cached result if available, otherwise triggers background computation."""
    from services.portfolio_simulation import run_portfolio_simulation
    import logging
    logger = logging.getLogger(__name__)

    db = request.app.db
    portfolio = await get_portfolio(db, strategy_type)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Check cache (12h TTL)
    cached = await db.portfolio_simulations.find_one(
        {"portfolio_type": strategy_type}, {"_id": 0}
    )
    if cached:
        cached_at = cached.get("computed_at", "")
        try:
            ct = datetime.fromisoformat(cached_at)
            if (datetime.now(timezone.utc) - ct.replace(tzinfo=timezone.utc)).total_seconds() < 43200:
                cached["status"] = "complete"
                return cached
        except Exception:
            pass

    # If already computing, return status
    if _simulation_locks.get(strategy_type):
        return {"status": "computing", "portfolio_type": strategy_type,
                "message": f"LSTM + Monte Carlo simulation in progress for {strategy_type}..."}

    # Trigger background computation
    holdings = portfolio.get("holdings", [])
    symbols = [h["symbol"] for h in holdings if h.get("symbol")]
    weights = [h.get("weight", 10.0) / 100.0 for h in holdings]
    portfolio_value = portfolio.get("current_value") or portfolio.get("actual_invested") or INITIAL_CAPITAL
    strategy_name = portfolio.get("name", strategy_type)

    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    def _run_simulation_bg():
        """Background thread to run simulation and store result."""
        import pymongo
        try:
            _simulation_locks[strategy_type] = True
            result = run_portfolio_simulation(symbols, weights, portfolio_value, strategy_name)
            if result.get("error"):
                logger.error(f"Simulation failed for {strategy_type}: {result['error']}")
                return

            result["portfolio_type"] = strategy_type
            result["computed_at"] = datetime.now(timezone.utc).isoformat()
            result["status"] = "complete"

            # Sanitize NaN/Inf
            def _sanitize(obj):
                if isinstance(obj, dict):
                    return {k: _sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                if isinstance(obj, float):
                    if math.isnan(obj) or math.isinf(obj):
                        return 0.0
                return obj

            result = _sanitize(result)

            # Store in MongoDB using sync client
            client = pymongo.MongoClient(mongo_url)
            sync_db = client[db_name]
            sync_db.portfolio_simulations.update_one(
                {"portfolio_type": strategy_type},
                {"$set": result},
                upsert=True,
            )
            client.close()
            logger.info(f"Simulation stored for {strategy_type}")
        except Exception as e:
            logger.error(f"Background simulation error for {strategy_type}: {e}")
        finally:
            _simulation_locks[strategy_type] = False

    thread = threading.Thread(target=_run_simulation_bg, daemon=True)
    thread.start()

    return {"status": "computing", "portfolio_type": strategy_type,
            "message": f"LSTM + Monte Carlo simulation started for {strategy_type}. Poll again in ~60s."}


@router.get("/portfolios/rebalance-log/{strategy_type}")
async def portfolio_rebalance_log(strategy_type: str, request: Request, limit: int = 20):
    db = request.app.db
    logs = await get_rebalance_log(db, strategy_type, limit)
    return {"logs": logs}


@router.get("/portfolios/exit-history/{strategy_type}")
async def portfolio_exit_history(strategy_type: str, request: Request):
    """Transparency view: every stock that was exited from this portfolio,
    with approximate entry/exit prices, qty, and the realized P&L that was
    removed from portfolio value.

    Reconstructs data for historical STOP_ENFORCED events (old logs lack
    entry_price/qty — we derive from yfinance close at portfolio.created_at
    and the weight gap in current holdings).
    """
    import yfinance as yf
    db = request.app.db
    portfolio = await get_portfolio(db, strategy_type)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    capital = float(portfolio.get("initial_capital", INITIAL_CAPITAL) or INITIAL_CAPITAL)
    created_at = portfolio.get("created_at")
    try:
        start_date = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")) if created_at else datetime.now(timezone.utc)
    except Exception:
        start_date = datetime.now(timezone.utc)

    # Current weight gap (proxy for how much "weight" was exited)
    current_weights = sum(float(h.get("weight", 0) or 0) for h in portfolio.get("holdings", []))
    lost_weight = max(0.0, 100.0 - current_weights)

    # Fetch all logs (STOP_ENFORCED + REBALANCE) for this portfolio
    logs = await db.portfolio_rebalance_log.find(
        {"portfolio_type": strategy_type}, {"_id": 0}
    ).sort("timestamp", 1).to_list(length=100)

    exits = []
    total_proceeds_removed = 0.0
    total_realized_pnl = 0.0
    total_cost_basis_lost = 0.0

    # Flatten all OUT changes
    out_events = []
    for log in logs:
        ts = log.get("timestamp", "")
        for ch in (log.get("changes") or []):
            if ch.get("type") == "OUT":
                out_events.append({"timestamp": ts, "change": ch, "action": log.get("action")})

    if not out_events:
        return {
            "strategy_type": strategy_type,
            "capital": round(capital, 2),
            "current_value": round(float(portfolio.get("current_value", capital) or capital), 2),
            "total_capital_removed": 0.0,
            "total_realized_pnl": 0.0,
            "exits": [],
            "explanation": "No exits yet — portfolio has not had any stop-outs or rebalances.",
        }

    # Derive per-event weight (split lost_weight evenly across logged exits
    # OR use authoritative data from the change if present)
    per_event_weight = (lost_weight / len(out_events)) if out_events else 0

    for evt in out_events:
        ch = evt["change"]
        sym = ch.get("symbol", "")
        symbol_clean = sym.replace(".NS", "")
        pnl_pct = float(ch.get("pnl_pct", 0) or ch.get("realized_pnl_pct", 0) or 0)

        # Use authoritative data if present (new code path)
        entry_price = float(ch.get("entry_price", 0) or 0)
        exit_price = float(ch.get("exit_price", 0) or 0)
        qty = int(ch.get("quantity", 0) or 0)
        realized_pnl = float(ch.get("realized_pnl", 0) or 0)
        proceeds = float(ch.get("proceeds", 0) or 0)

        # Reconstruct if missing (old STOP_ENFORCED logs)
        estimated = False
        if not entry_price or not qty:
            estimated = True
            # Fetch historical price at portfolio creation date
            try:
                tk = yf.Ticker(sym)
                # Get 5-day window around created_at to find nearest trading day
                from_dt = start_date - timedelta(days=5)
                to_dt = start_date + timedelta(days=5)
                hist = tk.history(start=from_dt.date(), end=to_dt.date())
                if hist is not None and len(hist) > 0:
                    entry_price = float(hist["Close"].iloc[0])
            except Exception:
                entry_price = 0.0

            # Estimate qty from weight gap
            cost_basis_estimate = capital * (per_event_weight / 100.0)
            if entry_price > 0:
                qty = int(cost_basis_estimate / entry_price)
            if qty < 1:
                qty = 1
            exit_price = round(entry_price * (1 + pnl_pct / 100.0), 2)
            realized_pnl = (exit_price - entry_price) * qty
            proceeds = exit_price * qty

        cost_basis = entry_price * qty if entry_price and qty else 0

        exits.append({
            "symbol": symbol_clean,
            "name": ch.get("name", symbol_clean),
            "buy_date": str(start_date.date()) if estimated else None,
            "exit_date": evt["timestamp"][:10] if evt["timestamp"] else None,
            "buy_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "quantity": qty,
            "cost_basis": round(cost_basis, 2),
            "proceeds": round(proceeds, 2),
            "realized_pnl": round(realized_pnl, 2),
            "realized_pnl_pct": round(pnl_pct, 2),
            "trigger": ch.get("trigger_type") or ("STOP_ENFORCED" if evt["action"] == "STOP_ENFORCED" else "REBALANCE"),
            "rationale": ch.get("rationale", ""),
            "capital_removed_from_portfolio": round(proceeds, 2),
            "estimated": estimated,
        })

        total_proceeds_removed += proceeds
        total_realized_pnl += realized_pnl
        total_cost_basis_lost += cost_basis

    current_value = float(portfolio.get("current_value", capital) or capital)
    # How much of the "missing" capital is explained by exits
    capital_drop = capital - current_value  # positive if portfolio is below capital

    return {
        "strategy_type": strategy_type,
        "name": portfolio.get("name", strategy_type),
        "capital": round(capital, 2),
        "current_value": round(current_value, 2),
        "capital_drop": round(capital_drop, 2),  # how much below ₹50L (positive = loss)
        "total_capital_removed": round(total_proceeds_removed, 2),
        "total_cost_basis_lost": round(total_cost_basis_lost, 2),
        "total_realized_pnl": round(total_realized_pnl, 2),
        "unrealized_pnl_on_remaining": round(current_value - (capital - total_proceeds_removed), 2) if total_proceeds_removed else round(current_value - capital, 2),
        "exits": exits,
        "explanation": (
            f"Each ₹50L portfolio lost capital when stocks were sold off. "
            f"These {len(exits)} exit(s) removed ₹{total_proceeds_removed/1e5:.2f}L from the portfolio "
            f"(cost basis ₹{total_cost_basis_lost/1e5:.2f}L + realized gain ₹{total_realized_pnl/1e5:.2f}L returned to the fund). "
            f"Remaining holdings are performing the residual P&L you see."
        ),
    }




@router.get("/portfolios/xirr/{strategy_type}")
async def portfolio_xirr(strategy_type: str, request: Request):
    """Compute XIRR for a portfolio based on investment date and current value."""
    db = request.app.db
    portfolio = await get_portfolio(db, strategy_type)
    if not portfolio or portfolio.get("status") != "active":
        raise HTTPException(status_code=404, detail="Active portfolio not found")

    # Basis for P&L and XIRR is the IMMUTABLE committed capital, not the
    # shrunken actual_invested (which gets eroded by stop-outs over time).
    capital = float(portfolio.get("initial_capital", INITIAL_CAPITAL) or INITIAL_CAPITAL)
    invested = float(portfolio.get("actual_invested", capital) or capital)
    current_value = float(portfolio.get("current_value", invested) or invested)
    created_at = portfolio.get("created_at")

    # Parse creation date
    if not created_at:
        return {"xirr_pct": None, "error": "No creation date"}

    try:
        if isinstance(created_at, str):
            start_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, datetime):
            start_date = created_at
        else:
            return {"xirr_pct": None, "error": "Invalid creation date"}
    except Exception:
        return {"xirr_pct": None, "error": "Cannot parse creation date"}

    now = datetime.now(timezone.utc)
    days_held = (now - start_date.replace(tzinfo=timezone.utc)).days
    if days_held <= 0:
        return {"xirr_pct": 0.0, "days_held": 0}

    # Cash flows: negative outflow at start, positive inflow now
    # XIRR baseline = COMMITTED CAPITAL (not shrunken invested)
    cash_flows = [(-capital, start_date), (current_value, now)]

    # Collect rebalance log flows if any (realized P&L from exits)
    rebal_logs = await get_rebalance_log(db, strategy_type, limit=50)
    log_realized_pnl = 0.0
    exit_count = 0
    for log in rebal_logs:
        for ch in (log.get("changes") or []):
            if ch.get("type") == "OUT" and ch.get("realized_pnl"):
                log_realized_pnl += ch["realized_pnl"]
                exit_count += 1

    # Prefer portfolio-level tracked realized_pnl (authoritative);
    # fall back to log aggregation for older portfolios
    realized_pnl = float(portfolio.get("realized_pnl", 0) or 0) or log_realized_pnl

    # Compute XIRR using Newton-Raphson
    def xirr(flows, guess=0.1):
        def npv(rate):
            return sum(
                cf / (1 + rate) ** ((dt - flows[0][1]).days / 365.25)
                for cf, dt in flows
            )

        def dnpv(rate):
            return sum(
                -((dt - flows[0][1]).days / 365.25) * cf / (1 + rate) ** ((dt - flows[0][1]).days / 365.25 + 1)
                for cf, dt in flows
            )

        rate = guess
        for _ in range(100):
            nv = npv(rate)
            dnv = dnpv(rate)
            if abs(dnv) < 1e-12:
                break
            rate -= nv / dnv
            if abs(nv) < 1e-6:
                break
        return rate

    try:
        if days_held < 7:
            # Too short for meaningful XIRR — use simple return vs capital
            xirr_pct = round((current_value - capital) / capital * 100, 2)
        else:
            xirr_val = xirr(cash_flows)
            xirr_pct = round(xirr_val * 100, 2)
            # Sanity cap: XIRR beyond ±500% is usually a numerical artifact
            if abs(xirr_pct) > 500:
                xirr_pct = round((current_value - capital) / capital * 100, 2)
    except Exception:
        # Fallback to simple return vs capital
        xirr_pct = round((current_value - capital) / capital * 100, 2)

    # Per-stock P&L breakdown (per-stock P&L is vs each stock's entry price,
    # which is unrelated to portfolio basis — keep as-is for stock-level view)
    holdings = portfolio.get("holdings", [])
    unrealized_pnl = sum(h.get("pnl", 0) or 0 for h in holdings)

    # Total portfolio P&L = current_value - committed_capital (HONEST)
    total_pnl = current_value - capital
    total_pnl_pct = (total_pnl / capital * 100) if capital > 0 else 0

    # Winners/losers
    winners = [h for h in holdings if (h.get("pnl_pct") or 0) > 0]
    losers = [h for h in holdings if (h.get("pnl_pct") or 0) < 0]

    return {
        "strategy_type": strategy_type,
        "xirr_pct": xirr_pct,
        "days_held": days_held,
        "capital": round(capital, 2),
        "invested": round(invested, 2),
        "current_value": round(current_value, 2),
        "cash_balance": round(float(portfolio.get("cash_balance", 0) or 0), 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": round(total_pnl_pct, 2),
        "realized_pnl": round(realized_pnl, 2),
        "exit_count": exit_count,
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate_pct": round(len(winners) / max(len(holdings), 1) * 100, 1),
        "top_gainer": {
            "symbol": max(holdings, key=lambda h: h.get("pnl_pct", 0)).get("symbol", "").replace(".NS", ""),
            "pnl_pct": round(max(h.get("pnl_pct", 0) for h in holdings), 2),
        } if holdings else None,
        "top_loser": {
            "symbol": min(holdings, key=lambda h: h.get("pnl_pct", 0)).get("symbol", "").replace(".NS", ""),
            "pnl_pct": round(min(h.get("pnl_pct", 0) for h in holdings), 2),
        } if holdings else None,
        "created_at": str(created_at),
    }


@router.get("/portfolios/walk-forward")
async def walk_forward_all(request: Request):
    """Get walk-forward tracking for all portfolios."""
    db = request.app.db
    records = await db.walk_forward_tracking.find(
        {}, {"_id": 0}
    ).sort("recorded_at", -1).to_list(length=200)
    return {"records": records, "total": len(records)}


@router.get("/portfolios/walk-forward/{strategy_type}")
async def walk_forward_detail(strategy_type: str, request: Request):
    """Get walk-forward forecast-vs-actual tracking for a specific portfolio."""
    db = request.app.db

    records = await db.walk_forward_tracking.find(
        {"portfolio_type": strategy_type}, {"_id": 0}
    ).sort("recorded_at", 1).to_list(length=100)

    if not records:
        # Try to create the first snapshot from current simulation + portfolio data
        sim = await db.portfolio_simulations.find_one(
            {"portfolio_type": strategy_type}, {"_id": 0}
        )
        portfolio = await get_portfolio(db, strategy_type)

        if sim and portfolio:
            snapshot = _build_walk_forward_snapshot(sim, portfolio, strategy_type)
            if snapshot:
                await db.walk_forward_tracking.insert_one(snapshot)
                snapshot.pop("_id", None)
                records = [snapshot]

    return {
        "portfolio_type": strategy_type,
        "records": records,
        "total": len(records),
    }


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


_rebuild_lock = {"running": False}


SUPERADMIN_EMAIL = "somnath.dey@smifs.com"


def _require_superadmin(request: Request):
    """Check JWT for superadmin. Raises 403 if not."""
    import jwt as pyjwt
    import os
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Authentication required")
    try:
        secret = os.environ.get("TOTP_JWT_SECRET", "bmia-jwt-secret")
        payload = pyjwt.decode(auth[7:], secret, algorithms=["HS256"])
        if payload.get("sub") != SUPERADMIN_EMAIL:
            raise HTTPException(status_code=403, detail="Superadmin access required")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid session")


@router.post("/portfolios/rebuild-all")
async def portfolio_rebuild_all(request: Request):
    """Delete all portfolios and trigger v3 reconstruction. SUPERADMIN ONLY."""
    _require_superadmin(request)

    if _rebuild_lock["running"]:
        return {"status": "already_running", "message": "Rebuild already in progress"}

    db = request.app.db

    # Count existing
    existing = await db.portfolios.find({"status": "active"}).to_list(length=20)
    existing_types = [p["type"] for p in existing]

    # Delete all portfolios, backtests, simulations
    del_p = await db.portfolios.delete_many({})
    del_bt = await db.portfolio_backtests.delete_many({})
    del_sim = await db.portfolio_simulations.delete_many({})
    del_wf = await db.walk_forward_tracking.delete_many({})

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"REBUILD: Deleted {del_p.deleted_count} portfolios, {del_bt.deleted_count} backtests, {del_sim.deleted_count} simulations, {del_wf.deleted_count} walk-forward records")

    return {
        "status": "triggered",
        "message": f"Deleted {del_p.deleted_count} portfolios ({', '.join(existing_types)}). The daemon will auto-reconstruct all 6 with hardened v3 pipeline. Monitor /api/portfolios/overview.",
        "cleared_caches": {
            "portfolios": del_p.deleted_count,
            "backtests": del_bt.deleted_count,
            "simulations": del_sim.deleted_count,
            "walk_forward": del_wf.deleted_count,
        },
    }


def _build_walk_forward_snapshot(sim: dict, portfolio: dict, strategy_type: str) -> dict:
    """Build a walk-forward snapshot from simulation prediction + current portfolio state."""
    mc = sim.get("monte_carlo", {})
    rm = mc.get("risk_metrics", {})
    ts = mc.get("terminal_stats", {})
    lstm = sim.get("lstm_forecast", {})

    portfolio_value = portfolio.get("current_value") or portfolio.get("actual_invested") or INITIAL_CAPITAL
    pnl_pct = portfolio.get("total_pnl_pct", 0)

    return {
        "portfolio_type": strategy_type,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "simulation_computed_at": sim.get("computed_at", ""),
        # Forecast at time of simulation
        "forecast": {
            "expected_return_pct": rm.get("expected_return_pct", 0),
            "median_return_pct": rm.get("median_return_pct", 0),
            "var_95_pct": rm.get("var_95_pct", 0),
            "probability_of_profit_pct": rm.get("probability_of_profit_pct", 0),
            "median_terminal_value": ts.get("median_value", 0),
            "lstm_annualized_return_pct": lstm.get("annualized_expected_return_pct", 0),
            "lstm_annualized_vol_pct": lstm.get("annualized_volatility_pct", 0),
        },
        # Actual at time of snapshot
        "actual": {
            "portfolio_value": portfolio_value,
            "total_pnl_pct": pnl_pct,
            "holdings_count": len(portfolio.get("holdings", [])),
        },
    }


@router.get("/portfolios")
async def portfolios_list(request: Request):
    db = request.app.db
    portfolios = await get_all_portfolios(db)
    return {"portfolios": portfolios, "strategies": PORTFOLIO_STRATEGIES}

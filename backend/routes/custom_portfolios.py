"""Custom Portfolio Routes — User-created manual portfolios with rebalancing and history tracking."""
import math
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["custom-portfolios"])

DEFAULT_CAPITAL = 5000000  # ₹50L


def _sf(val, default=0.0):
    if val is None:
        return default
    try:
        v = float(val)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def _serialize(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


class CreatePortfolioReq(BaseModel):
    name: str
    symbols: list  # [{"symbol": "TCS.NS", "weight": 15}, ...]
    capital: float = DEFAULT_CAPITAL


class RebalanceReq(BaseModel):
    symbols: list  # New full list of holdings with weights


def _fetch_prices(symbols: list) -> dict:
    """Fetch current prices for a list of symbols."""
    import yfinance as yf
    prices = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if price and price > 0:
                prices[sym] = _sf(price)
            else:
                hist = t.history(period="5d")
                if hist is not None and len(hist) > 0:
                    prices[sym] = _sf(float(hist["Close"].iloc[-1]))
        except Exception as e:
            logger.debug(f"Price fetch failed for {sym}: {e}")
    return prices


def _build_holdings(symbols_weights: list, prices: dict, capital: float) -> list:
    """Build holdings array with quantities and values from weights + prices."""
    import yfinance as yf

    # Normalize weights to 100%
    total_weight = sum(s.get("weight", 0) for s in symbols_weights) or 100
    holdings = []
    total_invested = 0

    for sw in symbols_weights:
        sym = sw["symbol"]
        weight = (sw.get("weight", 0) / total_weight) * 100
        price = prices.get(sym, 0)
        if price <= 0:
            continue

        allocated = capital * (weight / 100)
        quantity = int(allocated / price)
        if quantity <= 0:
            quantity = 1
        value = round(quantity * price, 2)
        total_invested += value

        # Get sector
        sector = "N/A"
        try:
            info = yf.Ticker(sym).info or {}
            sector = info.get("sector", "N/A")
        except Exception:
            pass

        holdings.append({
            "symbol": sym,
            "name": sw.get("name", sym.replace(".NS", "")),
            "sector": sector,
            "entry_price": round(price, 2),
            "current_price": round(price, 2),
            "quantity": quantity,
            "weight": round(weight, 1),
            "value": value,
            "pnl": 0,
            "pnl_pct": 0,
        })

    return holdings, total_invested


@router.post("/custom-portfolios")
async def create_custom_portfolio(req: CreatePortfolioReq, request: Request):
    """Create a new custom portfolio."""
    db = request.app.db

    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Portfolio name is required")
    if not req.symbols or len(req.symbols) == 0:
        raise HTTPException(status_code=400, detail="At least 1 stock required")
    if len(req.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 stocks allowed")

    # Check for duplicates
    existing = await db.custom_portfolios.count_documents({})
    if existing >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 custom portfolios allowed")

    symbol_list = [s["symbol"] for s in req.symbols]
    prices = _fetch_prices(symbol_list)

    if not prices:
        raise HTTPException(status_code=400, detail="Could not fetch prices for any stock")

    holdings, total_invested = _build_holdings(req.symbols, prices, req.capital)

    if not holdings:
        raise HTTPException(status_code=400, detail="No valid holdings after price fetch")

    doc = {
        "name": req.name.strip(),
        "capital": req.capital,
        "holdings": holdings,
        "status": "active",
        "total_invested": round(total_invested, 2),
        "current_value": round(total_invested, 2),
        "total_pnl": 0,
        "total_pnl_pct": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rebalance_count": 0,
    }

    result = await db.custom_portfolios.insert_one(doc)
    portfolio_id = str(result.inserted_id)

    # Log creation
    await db.custom_portfolio_history.insert_one({
        "portfolio_id": portfolio_id,
        "action": "CREATED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changes": [{"type": "ADD", "symbol": h["symbol"], "name": h["name"], "weight": h["weight"]} for h in holdings],
        "snapshot": {"holdings": holdings, "total_invested": total_invested},
    })

    # Return clean copy without _id
    doc.pop("_id", None)
    doc["id"] = portfolio_id
    return doc


@router.get("/custom-portfolios")
async def list_custom_portfolios(request: Request):
    """List all custom portfolios."""
    db = request.app.db
    cursor = db.custom_portfolios.find({}).sort("created_at", -1)
    portfolios = []
    for doc in await cursor.to_list(length=20):
        portfolios.append(_serialize(doc))
    return {"portfolios": portfolios}


@router.get("/custom-portfolios/{portfolio_id}")
async def get_custom_portfolio(portfolio_id: str, request: Request):
    """Get a custom portfolio with refreshed prices."""
    from bson import ObjectId
    db = request.app.db

    doc = await db.custom_portfolios.find_one({"_id": ObjectId(portfolio_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Refresh prices
    holdings = doc.get("holdings", [])
    symbols = [h["symbol"] for h in holdings]
    prices = _fetch_prices(symbols)

    total_value = 0
    for h in holdings:
        new_price = prices.get(h["symbol"])
        if new_price and new_price > 0:
            h["current_price"] = round(new_price, 2)
            h["value"] = round(h["quantity"] * new_price, 2)
            if h["entry_price"] > 0:
                h["pnl_pct"] = round((new_price - h["entry_price"]) / h["entry_price"] * 100, 2)
                h["pnl"] = round((new_price - h["entry_price"]) * h["quantity"], 2)
        total_value += h.get("value", 0)

    total_invested = doc.get("total_invested", 0)
    total_pnl = round(total_value - total_invested, 2)
    total_pnl_pct = round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2)

    await db.custom_portfolios.update_one(
        {"_id": ObjectId(portfolio_id)},
        {"$set": {
            "holdings": holdings,
            "current_value": round(total_value, 2),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    doc["current_value"] = round(total_value, 2)
    doc["total_pnl"] = total_pnl
    doc["total_pnl_pct"] = total_pnl_pct
    return _serialize(doc)


@router.put("/custom-portfolios/{portfolio_id}/rebalance")
async def rebalance_custom_portfolio(portfolio_id: str, req: RebalanceReq, request: Request):
    """Rebalance a custom portfolio — swap stocks, adjust weights."""
    from bson import ObjectId
    db = request.app.db

    doc = await db.custom_portfolios.find_one({"_id": ObjectId(portfolio_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if len(req.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 stocks allowed")

    old_holdings = {h["symbol"]: h for h in doc.get("holdings", [])}
    old_symbols = set(old_holdings.keys())
    new_symbols_set = set(s["symbol"] for s in req.symbols)

    # Compute changes
    changes = []
    for s in req.symbols:
        if s["symbol"] not in old_symbols:
            changes.append({"type": "ADD", "symbol": s["symbol"], "weight": s.get("weight", 10)})
        elif old_holdings[s["symbol"]].get("weight") != s.get("weight"):
            changes.append({"type": "WEIGHT_CHANGE", "symbol": s["symbol"],
                           "old_weight": old_holdings[s["symbol"]].get("weight"),
                           "new_weight": s.get("weight", 10)})
    for sym in old_symbols - new_symbols_set:
        changes.append({"type": "REMOVE", "symbol": sym})

    # Build new holdings
    symbol_list = [s["symbol"] for s in req.symbols]
    prices = _fetch_prices(symbol_list)
    capital = doc.get("capital", DEFAULT_CAPITAL)
    holdings, total_invested = _build_holdings(req.symbols, prices, capital)

    if not holdings:
        raise HTTPException(status_code=400, detail="No valid holdings after rebalance")

    rebalance_count = doc.get("rebalance_count", 0) + 1

    await db.custom_portfolios.update_one(
        {"_id": ObjectId(portfolio_id)},
        {"$set": {
            "holdings": holdings,
            "total_invested": round(total_invested, 2),
            "current_value": round(total_invested, 2),
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "rebalance_count": rebalance_count,
        }}
    )

    # Log rebalance
    await db.custom_portfolio_history.insert_one({
        "portfolio_id": portfolio_id,
        "action": "REBALANCED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "snapshot": {"holdings": holdings, "total_invested": total_invested},
    })

    doc["holdings"] = holdings
    doc["total_invested"] = round(total_invested, 2)
    doc["rebalance_count"] = rebalance_count
    doc.pop("_id", None)
    doc["id"] = portfolio_id
    return doc


@router.get("/custom-portfolios/{portfolio_id}/history")
async def custom_portfolio_history(portfolio_id: str, request: Request):
    """Get rebalance history for a custom portfolio."""
    db = request.app.db
    cursor = db.custom_portfolio_history.find(
        {"portfolio_id": portfolio_id}, {"_id": 0}
    ).sort("timestamp", -1).limit(50)
    history = await cursor.to_list(length=50)
    return {"history": history, "total": len(history)}


@router.delete("/custom-portfolios/{portfolio_id}")
async def delete_custom_portfolio(portfolio_id: str, request: Request):
    """Delete a custom portfolio."""
    from bson import ObjectId
    db = request.app.db
    result = await db.custom_portfolios.delete_one({"_id": ObjectId(portfolio_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    await db.custom_portfolio_history.delete_many({"portfolio_id": portfolio_id})
    return {"status": "deleted"}


_custom_backtest_locks = {}
_custom_sim_locks = {}


@router.get("/custom-portfolios/{portfolio_id}/backtest")
async def custom_portfolio_backtest(portfolio_id: str, request: Request):
    """5-year backtest for a custom portfolio. Background computation + cache."""
    from bson import ObjectId
    from services.portfolio_hardening import compute_backtest
    import threading
    import os
    import pymongo

    db = request.app.db
    doc = await db.custom_portfolios.find_one({"_id": ObjectId(portfolio_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    cache_key = f"custom_{portfolio_id}"
    cached = await db.portfolio_backtests.find_one({"portfolio_type": cache_key}, {"_id": 0})
    if cached:
        try:
            ct = datetime.fromisoformat(cached.get("computed_at", ""))
            if (datetime.now(timezone.utc) - ct.replace(tzinfo=timezone.utc)).total_seconds() < 86400:
                cached["status"] = "complete"
                return cached
        except Exception:
            pass

    if _custom_backtest_locks.get(portfolio_id):
        return {"status": "computing", "portfolio_type": cache_key}

    symbols = [h["symbol"] for h in doc.get("holdings", []) if h.get("symbol")]
    name = doc.get("name", "Custom Portfolio")
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    def _run():
        try:
            _custom_backtest_locks[portfolio_id] = True
            result = compute_backtest(symbols, name)
            result["portfolio_type"] = cache_key
            result["computed_at"] = datetime.now(timezone.utc).isoformat()
            result["status"] = "complete"
            client = pymongo.MongoClient(mongo_url)
            client[db_name].portfolio_backtests.update_one(
                {"portfolio_type": cache_key}, {"$set": result}, upsert=True)
            client.close()
        except Exception as e:
            logger.error(f"Custom backtest error: {e}")
        finally:
            _custom_backtest_locks[portfolio_id] = False

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "computing", "portfolio_type": cache_key}


@router.get("/custom-portfolios/{portfolio_id}/simulation")
async def custom_portfolio_simulation(portfolio_id: str, request: Request):
    """LSTM + Monte Carlo simulation for a custom portfolio. Background computation + cache."""
    from bson import ObjectId
    from services.portfolio_simulation import run_portfolio_simulation
    import threading
    import os
    import pymongo

    db = request.app.db
    doc = await db.custom_portfolios.find_one({"_id": ObjectId(portfolio_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    cache_key = f"custom_{portfolio_id}"
    cached = await db.portfolio_simulations.find_one({"portfolio_type": cache_key}, {"_id": 0})
    if cached:
        try:
            ct = datetime.fromisoformat(cached.get("computed_at", ""))
            if (datetime.now(timezone.utc) - ct.replace(tzinfo=timezone.utc)).total_seconds() < 43200:
                cached["status"] = "complete"
                return cached
        except Exception:
            pass

    if _custom_sim_locks.get(portfolio_id):
        return {"status": "computing", "portfolio_type": cache_key}

    holdings = doc.get("holdings", [])
    symbols = [h["symbol"] for h in holdings if h.get("symbol")]
    weights = [h.get("weight", 10) / 100 for h in holdings]
    value = doc.get("current_value") or doc.get("total_invested") or 5000000
    name = doc.get("name", "Custom Portfolio")
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    def _run():
        import math
        try:
            _custom_sim_locks[portfolio_id] = True
            result = run_portfolio_simulation(symbols, weights, value, name)
            if result.get("error"):
                return
            result["portfolio_type"] = cache_key
            result["computed_at"] = datetime.now(timezone.utc).isoformat()
            result["status"] = "complete"

            def _sanitize(obj):
                if isinstance(obj, dict):
                    return {k: _sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                    return 0.0
                return obj

            result = _sanitize(result)
            client = pymongo.MongoClient(mongo_url)
            client[db_name].portfolio_simulations.update_one(
                {"portfolio_type": cache_key}, {"$set": result}, upsert=True)
            client.close()
        except Exception as e:
            logger.error(f"Custom simulation error: {e}")
        finally:
            _custom_sim_locks[portfolio_id] = False

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "computing", "portfolio_type": cache_key}


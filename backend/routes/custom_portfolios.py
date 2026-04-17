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
        "holdings_value": round(total_invested, 2),
        "cash_balance": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
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

    holdings_value = 0
    for h in holdings:
        new_price = prices.get(h["symbol"])
        if new_price and new_price > 0:
            h["current_price"] = round(new_price, 2)
            h["value"] = round(h["quantity"] * new_price, 2)
            if h["entry_price"] > 0:
                h["pnl_pct"] = round((new_price - h["entry_price"]) / h["entry_price"] * 100, 2)
                h["pnl"] = round((new_price - h["entry_price"]) * h["quantity"], 2)
        holdings_value += h.get("value", 0)

    # Proper accounting: current_value = holdings value + cash balance
    cash_balance = _sf(doc.get("cash_balance", 0))
    realized_pnl = _sf(doc.get("realized_pnl", 0))
    total_value = holdings_value + cash_balance

    # Total invested = original capital deployed (immutable basis)
    total_invested = _sf(doc.get("total_invested", doc.get("capital", DEFAULT_CAPITAL)))

    unrealized_pnl = round(sum(h.get("pnl", 0) or 0 for h in holdings), 2)
    total_pnl = round(realized_pnl + unrealized_pnl, 2)
    total_pnl_pct = round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2)

    await db.custom_portfolios.update_one(
        {"_id": ObjectId(portfolio_id)},
        {"$set": {
            "holdings": holdings,
            "current_value": round(total_value, 2),
            "holdings_value": round(holdings_value, 2),
            "cash_balance": round(cash_balance, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    doc["current_value"] = round(total_value, 2)
    doc["holdings_value"] = round(holdings_value, 2)
    doc["cash_balance"] = round(cash_balance, 2)
    doc["realized_pnl"] = round(realized_pnl, 2)
    doc["unrealized_pnl"] = unrealized_pnl
    doc["total_pnl"] = total_pnl
    doc["total_pnl_pct"] = total_pnl_pct
    return _serialize(doc)


@router.put("/custom-portfolios/{portfolio_id}/rebalance")
async def rebalance_custom_portfolio(portfolio_id: str, req: RebalanceReq, request: Request):
    """Rebalance a custom portfolio with proper accounting.

    Preserves cost basis for kept stocks, realizes P&L on sells, and
    tracks a cash_balance for sell proceeds. Total invested (initial
    capital basis) is never reset — gains are locked in as realized P&L.
    """
    from bson import ObjectId
    import yfinance as yf
    db = request.app.db

    doc = await db.custom_portfolios.find_one({"_id": ObjectId(portfolio_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if len(req.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 stocks allowed")
    if len(req.symbols) == 0:
        raise HTTPException(status_code=400, detail="At least 1 stock required")

    old_holdings = doc.get("holdings", [])
    old_map = {h["symbol"]: h for h in old_holdings}
    old_syms = set(old_map.keys())
    new_syms = set(s["symbol"] for s in req.symbols)

    # Refresh prices for the union of symbols (so current_price is always fresh)
    all_symbols = list(old_syms | new_syms)
    prices = _fetch_prices(all_symbols)
    if not prices:
        raise HTTPException(status_code=400, detail="Could not fetch prices")

    # Update current prices on old holdings
    for h in old_holdings:
        p = prices.get(h["symbol"])
        if p and p > 0:
            h["current_price"] = round(p, 2)

    # Current portfolio value V = holdings value + cash balance
    cash_balance = _sf(doc.get("cash_balance", 0))
    realized_pnl = _sf(doc.get("realized_pnl", 0))
    holdings_value = sum(
        _sf(h.get("current_price", h.get("entry_price", 0))) * h.get("quantity", 0)
        for h in old_holdings
    )
    V = holdings_value + cash_balance

    # Normalize new weights to 100%
    total_weight = sum(_sf(s.get("weight", 0)) for s in req.symbols) or 100
    new_weight_map = {
        s["symbol"]: (_sf(s.get("weight", 0)) / total_weight) * 100
        for s in req.symbols
    }
    new_meta_map = {s["symbol"]: s for s in req.symbols}

    changes = []
    new_holdings = []

    # ---- Step 1: Sell removed stocks (full exit) ----
    for sym in old_syms - new_syms:
        h = old_map[sym]
        cp = _sf(h.get("current_price", h.get("entry_price", 0)))
        ep = _sf(h.get("entry_price", 0))
        qty = h.get("quantity", 0)
        pnl = (cp - ep) * qty
        realized_pnl += pnl
        cash_balance += cp * qty
        changes.append({
            "type": "OUT",
            "symbol": sym,
            "name": h.get("name", ""),
            "quantity": qty,
            "entry_price": round(ep, 2),
            "exit_price": round(cp, 2),
            "realized_pnl": round(pnl, 2),
            "realized_pnl_pct": round((cp - ep) / ep * 100, 2) if ep > 0 else 0,
        })

    # ---- Step 2: Kept stocks — rebalance only if weight changed ----
    for sym in old_syms & new_syms:
        h = dict(old_map[sym])  # shallow copy
        cp = _sf(prices.get(sym, h.get("current_price", h.get("entry_price", 0))))
        if cp <= 0:
            cp = _sf(h.get("entry_price", 0))
        old_w = _sf(h.get("weight", 0))
        new_w = new_weight_map[sym]

        # If weight essentially unchanged, preserve holding completely
        if abs(old_w - new_w) < 0.5:
            h["current_price"] = round(cp, 2)
            h["weight"] = round(new_w, 1)
            h["value"] = round(cp * h["quantity"], 2)
            if h["entry_price"] > 0:
                h["pnl"] = round((cp - h["entry_price"]) * h["quantity"], 2)
                h["pnl_pct"] = round((cp - h["entry_price"]) / h["entry_price"] * 100, 2)
            new_holdings.append(h)
            continue

        # Weight changed — resize position to target value
        target_value = V * new_w / 100
        current_value = cp * h["quantity"]

        if target_value > current_value + cp:  # buy more (at least 1 share)
            extra_qty = int((target_value - current_value) / cp)
            if extra_qty > 0 and extra_qty * cp <= cash_balance + 1:
                new_qty = h["quantity"] + extra_qty
                # Weighted avg entry price
                new_entry = ((_sf(h["entry_price"]) * h["quantity"]) + (cp * extra_qty)) / new_qty
                cash_balance -= extra_qty * cp
                h["quantity"] = new_qty
                h["entry_price"] = round(new_entry, 2)
                changes.append({
                    "type": "BUY_MORE",
                    "symbol": sym,
                    "name": h.get("name", ""),
                    "additional_quantity": extra_qty,
                    "price": round(cp, 2),
                })
        elif target_value < current_value - cp:  # sell some
            sell_qty = int((current_value - target_value) / cp)
            if 0 < sell_qty < h["quantity"]:
                ep = _sf(h.get("entry_price", 0))
                pnl = (cp - ep) * sell_qty
                realized_pnl += pnl
                cash_balance += sell_qty * cp
                h["quantity"] -= sell_qty
                changes.append({
                    "type": "SELL_PARTIAL",
                    "symbol": sym,
                    "name": h.get("name", ""),
                    "quantity_sold": sell_qty,
                    "price": round(cp, 2),
                    "realized_pnl": round(pnl, 2),
                })

        h["current_price"] = round(cp, 2)
        h["weight"] = round(new_w, 1)
        h["value"] = round(cp * h["quantity"], 2)
        if h["entry_price"] > 0:
            h["pnl"] = round((cp - h["entry_price"]) * h["quantity"], 2)
            h["pnl_pct"] = round((cp - h["entry_price"]) / h["entry_price"] * 100, 2)
        new_holdings.append(h)

    # ---- Step 3: Buy added stocks ----
    for sym in new_syms - old_syms:
        cp = _sf(prices.get(sym, 0))
        if cp <= 0:
            continue
        new_w = new_weight_map[sym]
        target_value = V * new_w / 100
        qty = int(target_value / cp)
        if qty < 1 and target_value >= cp:
            qty = 1
        # Cap to available cash
        if qty * cp > cash_balance + 1:
            qty = int(cash_balance / cp)
        if qty < 1:
            continue
        cost = qty * cp
        cash_balance -= cost

        sector = "N/A"
        name = new_meta_map[sym].get("name", sym.replace(".NS", ""))
        try:
            info = yf.Ticker(sym).info or {}
            sector = info.get("sector", "N/A")
        except Exception:
            pass

        new_holdings.append({
            "symbol": sym,
            "name": name,
            "sector": sector,
            "entry_price": round(cp, 2),
            "current_price": round(cp, 2),
            "quantity": qty,
            "weight": round(new_w, 1),
            "value": round(cost, 2),
            "pnl": 0,
            "pnl_pct": 0,
            "entry_date": datetime.now(timezone.utc).isoformat(),
        })
        changes.append({
            "type": "IN",
            "symbol": sym,
            "name": name,
            "quantity": qty,
            "entry_price": round(cp, 2),
        })

    # ---- Finalize: compute accounting ----
    holdings_value = sum(h["current_price"] * h["quantity"] for h in new_holdings)
    current_value = holdings_value + cash_balance
    total_invested = _sf(doc.get("total_invested", doc.get("capital", DEFAULT_CAPITAL)))
    unrealized_pnl = sum(
        (h["current_price"] - h["entry_price"]) * h["quantity"]
        for h in new_holdings if h.get("entry_price", 0) > 0
    )
    total_pnl = realized_pnl + unrealized_pnl
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    rebalance_count = doc.get("rebalance_count", 0) + 1

    update_fields = {
        "holdings": new_holdings,
        "current_value": round(current_value, 2),
        "holdings_value": round(holdings_value, 2),
        "cash_balance": round(cash_balance, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rebalance_count": rebalance_count,
        "last_rebalanced": datetime.now(timezone.utc).isoformat(),
    }
    await db.custom_portfolios.update_one(
        {"_id": ObjectId(portfolio_id)},
        {"$set": update_fields},
    )

    # Log rebalance
    await db.custom_portfolio_history.insert_one({
        "portfolio_id": portfolio_id,
        "action": "REBALANCED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "snapshot": {
            "pre_value": round(V, 2),
            "post_value": round(current_value, 2),
            "realized_pnl_total": round(realized_pnl, 2),
            "cash_balance": round(cash_balance, 2),
        },
    })

    # Return updated doc
    doc.update(update_fields)
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


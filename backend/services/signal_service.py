"""
Signal Service - CRUD, evaluation, and tracking of AI-generated trade signals.
"""
import logging
from datetime import datetime, timedelta
from bson import ObjectId

logger = logging.getLogger(__name__)


def serialize_signal(doc):
    """Convert MongoDB doc to JSON-serializable dict."""
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d


async def save_signal(db, signal_data: dict, raw_analysis: dict = None):
    """Persist a new signal to MongoDB."""
    doc = {
        "symbol": signal_data.get("symbol"),
        "action": signal_data.get("action", "HOLD"),
        "timeframe": signal_data.get("timeframe", "SWING"),
        "horizon_days": signal_data.get("horizon_days", 14),
        "entry": signal_data.get("entry", {}),
        "targets": signal_data.get("targets", []),
        "stop_loss": signal_data.get("stop_loss", {}),
        "confidence": signal_data.get("confidence", 50),
        "key_theses": signal_data.get("key_theses", []),
        "invalidators": signal_data.get("invalidators", []),
        "risk_reward_ratio": signal_data.get("risk_reward_ratio", "N/A"),
        "position_sizing_hint": signal_data.get("position_sizing_hint", ""),
        "sector_context": signal_data.get("sector_context", ""),
        "detailed_reasoning": signal_data.get("detailed_reasoning", ""),
        "provider": signal_data.get("provider", "openai"),
        "model": signal_data.get("model", ""),
        # God Mode fields
        "god_mode": signal_data.get("god_mode", False),
        "agreement_level": signal_data.get("agreement_level"),
        "model_votes": signal_data.get("model_votes"),
        "models_succeeded": signal_data.get("models_succeeded"),
        "god_mode_consensus": {
            "distilled_action": signal_data.get("action"),
            "agreement_level": signal_data.get("agreement_level"),
            "model_signals": signal_data.get("model_votes"),
            "synthesized_rationale": signal_data.get("detailed_reasoning", ""),
        } if signal_data.get("god_mode") else None,
        "status": "OPEN",
        "entry_price": signal_data.get("entry", {}).get("price", 0),
        "current_price": signal_data.get("entry", {}).get("price", 0),
        "return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "peak_return_pct": 0.0,
        "days_open": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "closed_at": None,
        "evaluation_notes": "",
    }

    result = await db.signals.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return serialize_signal(doc)


async def get_active_signals(db, symbol: str = None):
    """Get all open signals, optionally filtered by symbol."""
    query = {"status": "OPEN"}
    if symbol:
        query["symbol"] = symbol
    cursor = db.signals.find(query, {"_id": 0}).sort("created_at", -1)
    results = await cursor.to_list(length=100)
    return [serialize_signal(r) for r in results]


async def get_signal_history(db, limit: int = 50, symbol: str = None, status: str = None):
    """Get signal history with optional filters."""
    query = {}
    if symbol:
        query["symbol"] = symbol
    if status:
        query["status"] = status
    cursor = db.signals.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    results = await cursor.to_list(length=limit)
    return [serialize_signal(r) for r in results]


async def evaluate_signal(db, signal_id: str, current_price: float):
    """Evaluate a single signal against current price and update status."""
    try:
        signal = await db.signals.find_one({"_id": ObjectId(signal_id)})
        if not signal:
            return {"error": "Signal not found"}

        if signal["status"] != "OPEN":
            return serialize_signal(signal)

        entry_price = signal.get("entry_price", 0)
        if entry_price <= 0:
            return serialize_signal(signal)

        action = signal.get("action", "HOLD")
        targets = signal.get("targets", [])
        stop_loss = signal.get("stop_loss", {})
        horizon_days = signal.get("horizon_days", 14)
        created_at = signal.get("created_at", datetime.now())

        # Calculate return
        if action == "BUY":
            return_pct = round((current_price - entry_price) / entry_price * 100, 2)
        elif action == "SELL":
            return_pct = round((entry_price - current_price) / entry_price * 100, 2)
        else:
            return_pct = 0.0

        # Track peak and drawdown
        peak_return = max(signal.get("peak_return_pct", 0), return_pct)
        max_dd = min(signal.get("max_drawdown_pct", 0), return_pct)

        days_open = (datetime.now() - created_at).days if isinstance(created_at, datetime) else 0

        # Determine status
        new_status = "OPEN"
        eval_notes = ""

        # Check targets (use first target)
        if targets and len(targets) > 0:
            target_price = targets[0].get("price", 0)
            if action == "BUY" and current_price >= target_price and target_price > 0:
                new_status = "HIT_TARGET"
                eval_notes = f"Target {target_price} hit at {current_price}. Return: {return_pct}%"
            elif action == "SELL" and current_price <= target_price and target_price > 0:
                new_status = "HIT_TARGET"
                eval_notes = f"Target {target_price} hit at {current_price}. Return: {return_pct}%"

        # Check stop loss
        stop_price = stop_loss.get("price", 0)
        if stop_price > 0:
            if action == "BUY" and current_price <= stop_price:
                new_status = "HIT_STOP"
                eval_notes = f"Stop loss {stop_price} triggered at {current_price}. Loss: {return_pct}%"
            elif action == "SELL" and current_price >= stop_price:
                new_status = "HIT_STOP"
                eval_notes = f"Stop loss {stop_price} triggered at {current_price}. Loss: {return_pct}%"

        # Check expiry
        if days_open >= horizon_days and new_status == "OPEN":
            new_status = "EXPIRED"
            eval_notes = f"Signal expired after {days_open} days. Final return: {return_pct}%"

        # Update signal
        update = {
            "$set": {
                "current_price": current_price,
                "return_pct": return_pct,
                "peak_return_pct": peak_return,
                "max_drawdown_pct": max_dd,
                "days_open": days_open,
                "status": new_status,
                "evaluation_notes": eval_notes,
                "updated_at": datetime.now(),
            }
        }
        if new_status != "OPEN":
            update["$set"]["closed_at"] = datetime.now()

        await db.signals.update_one({"_id": ObjectId(signal_id)}, update)

        # If closed, save evaluation record
        if new_status != "OPEN":
            await db.signal_evaluations.insert_one({
                "signal_id": signal_id,
                "symbol": signal["symbol"],
                "action": action,
                "entry_price": entry_price,
                "exit_price": current_price,
                "return_pct": return_pct,
                "status": new_status,
                "days_open": days_open,
                "max_drawdown_pct": max_dd,
                "peak_return_pct": peak_return,
                "notes": eval_notes,
                "evaluated_at": datetime.now(),
            })

        updated = await db.signals.find_one({"_id": ObjectId(signal_id)})
        return serialize_signal(updated)

    except Exception as e:
        logger.error(f"Evaluation error for signal {signal_id}: {e}")
        return {"error": str(e)}


async def evaluate_all_signals(db):
    """Evaluate all open signals against current prices."""
    from services.market_service import get_market_snapshot

    open_signals = await get_active_signals(db)
    results = []

    for signal in open_signals:
        symbol = signal.get("symbol")
        try:
            market = get_market_snapshot(symbol, "5d", "1d")
            if "error" not in market:
                current_price = market["latest"]["close"]
                result = await evaluate_signal(db, signal["_id"], current_price)
                results.append(result)
        except Exception as e:
            logger.error(f"Batch eval error for {symbol}: {e}")

    return results

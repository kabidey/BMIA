"""
Signal Service - CRUD, evaluation, and tracking of AI-generated trade signals.
HARDENED: Code-enforced bounds on entry/target/stop-loss, NaN sanitization.
"""
import math
import logging
from datetime import datetime, timedelta
from bson import ObjectId

logger = logging.getLogger(__name__)


def _safe_float(val, default=0.0):
    """Sanitize float — replace NaN/Inf with default."""
    if val is None:
        return default
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _validate_signal_bounds(signal_data: dict) -> dict:
    """Code-enforced guardrails on LLM-generated signal data.
    Fixes impossible entry/target/stop-loss relationships."""
    action = signal_data.get("action", "HOLD")
    entry = signal_data.get("entry", {})
    targets = signal_data.get("targets", [])
    stop_loss = signal_data.get("stop_loss", {})

    entry_price = _safe_float(entry.get("price"))
    if entry_price <= 0:
        return signal_data  # Can't validate without entry price

    # Validate confidence: clamp to 10-95
    conf = signal_data.get("confidence", 50)
    signal_data["confidence"] = max(10, min(95, int(_safe_float(conf, 50))))

    # Validate horizon_days: clamp to 1-90
    hd = signal_data.get("horizon_days", 14)
    signal_data["horizon_days"] = max(1, min(90, int(_safe_float(hd, 14))))

    # Validate targets
    clean_targets = []
    for t in targets:
        tp = _safe_float(t.get("price"))
        if tp <= 0:
            continue
        if action == "BUY" and tp <= entry_price:
            # Target must be ABOVE entry for BUY — fix by adding min 2% upside
            tp = round(entry_price * 1.02, 2)
            logger.warning(f"Signal hardening: BUY target {t.get('price')} <= entry {entry_price}, adjusted to {tp}")
        elif action == "SELL" and tp >= entry_price:
            # Target must be BELOW entry for SELL — fix by adding min 2% downside
            tp = round(entry_price * 0.98, 2)
            logger.warning(f"Signal hardening: SELL target {t.get('price')} >= entry {entry_price}, adjusted to {tp}")
        # Cap target at ±30% from entry (no moonshot hallucinations)
        if action == "BUY":
            tp = min(tp, round(entry_price * 1.30, 2))
        elif action == "SELL":
            tp = max(tp, round(entry_price * 0.70, 2))
        clean_targets.append({"price": tp, "label": t.get("label", "T1")})
    signal_data["targets"] = clean_targets if clean_targets else targets

    # Validate stop-loss
    sl_price = _safe_float(stop_loss.get("price"))
    if sl_price > 0:
        if action == "BUY" and sl_price >= entry_price:
            # Stop must be BELOW entry for BUY
            sl_price = round(entry_price * 0.95, 2)
            logger.warning(f"Signal hardening: BUY stop {stop_loss.get('price')} >= entry, adjusted to {sl_price}")
        elif action == "SELL" and sl_price <= entry_price:
            # Stop must be ABOVE entry for SELL
            sl_price = round(entry_price * 1.05, 2)
            logger.warning(f"Signal hardening: SELL stop {stop_loss.get('price')} <= entry, adjusted to {sl_price}")
        # Enforce max 15% stop-loss distance
        if action == "BUY":
            sl_price = max(sl_price, round(entry_price * 0.85, 2))
        elif action == "SELL":
            sl_price = min(sl_price, round(entry_price * 1.15, 2))
        signal_data["stop_loss"] = {"price": sl_price, "type": stop_loss.get("type", "hard")}

    # Compute and validate risk/reward ratio
    if clean_targets and sl_price > 0:
        if action == "BUY":
            reward = clean_targets[0]["price"] - entry_price
            risk = entry_price - sl_price
        elif action == "SELL":
            reward = entry_price - clean_targets[0]["price"]
            risk = sl_price - entry_price
        else:
            reward, risk = 0, 1
        rr = round(reward / max(risk, 0.01), 2)
        signal_data["risk_reward_ratio"] = f"1:{rr}"

    return signal_data


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
    """Persist a new signal to MongoDB. Applies code-enforced guardrails first."""
    # HARDENED: Validate signal bounds before saving
    signal_data = _validate_signal_bounds(signal_data)

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
    cursor = db.signals.find(query).sort("created_at", -1)
    results = await cursor.to_list(length=100)
    return [serialize_signal(r) for r in results]


async def get_signal_history(db, limit: int = 50, symbol: str = None, status: str = None):
    """Get signal history with optional filters."""
    query = {}
    if symbol:
        query["symbol"] = symbol
    if status:
        query["status"] = status
    cursor = db.signals.find(query).sort("created_at", -1).limit(limit)
    results = await cursor.to_list(length=limit)
    return [serialize_signal(r) for r in results]


async def evaluate_signal(db, signal_id: str, current_price: float):
    """Evaluate a single signal against current price and update status.
    HARDENED: Sanitizes all float calculations."""
    try:
        signal = await db.signals.find_one({"_id": ObjectId(signal_id)})
        if not signal:
            return {"error": "Signal not found"}

        if signal["status"] != "OPEN":
            return serialize_signal(signal)

        entry_price = _safe_float(signal.get("entry_price"))
        current_price = _safe_float(current_price)
        if entry_price <= 0 or current_price <= 0:
            return serialize_signal(signal)

        action = signal.get("action", "HOLD")
        targets = signal.get("targets", [])
        stop_loss = signal.get("stop_loss", {})
        horizon_days = signal.get("horizon_days", 14)
        created_at = signal.get("created_at", datetime.now())

        # Calculate return (sanitized)
        if action == "SELL":
            return_pct = _safe_float(round((entry_price - current_price) / entry_price * 100, 2))
        else:
            return_pct = _safe_float(round((current_price - entry_price) / entry_price * 100, 2))

        # Clamp return to ±100% (reject garbage)
        return_pct = max(-100.0, min(100.0, return_pct))

        # Track peak and drawdown (sanitized)
        peak_return = max(_safe_float(signal.get("peak_return_pct")), return_pct)
        max_dd = min(_safe_float(signal.get("max_drawdown_pct")), return_pct)

        days_open = (datetime.now() - created_at).days if isinstance(created_at, datetime) else 0

        # Determine status
        new_status = "OPEN"
        eval_notes = ""

        # Check targets (use first target) — sanitized
        if targets and len(targets) > 0:
            target_price = _safe_float(targets[0].get("price"))
            if action == "BUY" and target_price > 0 and current_price >= target_price:
                new_status = "HIT_TARGET"
                eval_notes = f"Target {target_price} hit at {current_price}. Return: {return_pct}%"
            elif action == "SELL" and target_price > 0 and current_price <= target_price:
                new_status = "HIT_TARGET"
                eval_notes = f"Target {target_price} hit at {current_price}. Return: {return_pct}%"

        # Check stop loss — sanitized
        stop_price = _safe_float(stop_loss.get("price"))
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
        if not symbol:
            continue
        try:
            market = get_market_snapshot(symbol, "5d", "1d")
            if "error" not in market:
                current_price = market["latest"]["close"]
                result = await evaluate_signal(db, signal["_id"], current_price)
                results.append(result)
        except Exception as e:
            logger.error(f"Batch eval error for {symbol}: {e}")

    return results

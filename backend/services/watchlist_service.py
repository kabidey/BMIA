"""
Watchlist Service — Portfolio tracking and watchlist persistence.
Stores user watchlist in MongoDB with live price tracking.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


async def add_to_watchlist(db, symbol: str, scrip_code: str = "", name: str = "",
                           notes: str = "", entry_price: float = 0, quantity: int = 0):
    """Add a stock to the watchlist."""
    existing = await db.watchlist.find_one({"symbol": symbol})
    if existing:
        # Update existing entry
        update = {"updated_at": datetime.now(IST).isoformat()}
        if notes:
            update["notes"] = notes
        if entry_price > 0:
            update["entry_price"] = entry_price
        if quantity > 0:
            update["quantity"] = quantity
        await db.watchlist.update_one({"symbol": symbol}, {"$set": update})
        return {"status": "updated", "symbol": symbol}

    doc = {
        "symbol": symbol.upper(),
        "scrip_code": scrip_code,
        "name": name,
        "notes": notes,
        "entry_price": entry_price,
        "quantity": quantity,
        "added_at": datetime.now(IST).isoformat(),
        "updated_at": datetime.now(IST).isoformat(),
    }
    await db.watchlist.insert_one(doc)
    return {"status": "added", "symbol": symbol}


async def remove_from_watchlist(db, symbol: str):
    """Remove a stock from the watchlist."""
    result = await db.watchlist.delete_one({"symbol": symbol.upper()})
    if result.deleted_count > 0:
        return {"status": "removed", "symbol": symbol}
    return {"status": "not_found", "symbol": symbol}


async def get_watchlist(db):
    """Get all watchlist items."""
    items = await db.watchlist.find({}, {"_id": 0}).sort("added_at", -1).to_list(length=200)
    return items


async def get_watchlist_with_prices(db):
    """Get watchlist with live BSE prices."""
    from services.bse_price_service import get_bse_quote

    items = await db.watchlist.find({}, {"_id": 0}).sort("added_at", -1).to_list(length=200)

    enriched = []
    for item in items:
        scrip_code = item.get("scrip_code", "")
        price_data = {}
        if scrip_code:
            price_data = get_bse_quote(scrip_code)

        entry = {**item}
        if price_data:
            entry["ltp"] = price_data.get("ltp", 0)
            entry["change"] = price_data.get("change", 0)
            entry["change_pct"] = price_data.get("change_pct", 0)
            entry["high"] = price_data.get("high", 0)
            entry["low"] = price_data.get("low", 0)
            entry["prev_close"] = price_data.get("prev_close", 0)

            if item.get("entry_price") and item["entry_price"] > 0 and price_data.get("ltp"):
                entry["pnl"] = round(price_data["ltp"] - item["entry_price"], 2)
                entry["pnl_pct"] = round(((price_data["ltp"] - item["entry_price"]) / item["entry_price"]) * 100, 2)
                if item.get("quantity", 0) > 0:
                    entry["total_pnl"] = round(entry["pnl"] * item["quantity"], 2)
                    entry["total_value"] = round(price_data["ltp"] * item["quantity"], 2)
                    entry["invested"] = round(item["entry_price"] * item["quantity"], 2)

        enriched.append(entry)

    return enriched


async def update_watchlist_item(db, symbol: str, notes: str = None,
                                 entry_price: float = None, quantity: int = None):
    """Update a watchlist item."""
    update = {"updated_at": datetime.now(IST).isoformat()}
    if notes is not None:
        update["notes"] = notes
    if entry_price is not None:
        update["entry_price"] = entry_price
    if quantity is not None:
        update["quantity"] = quantity

    result = await db.watchlist.update_one({"symbol": symbol.upper()}, {"$set": update})
    if result.matched_count > 0:
        return {"status": "updated", "symbol": symbol}
    return {"status": "not_found", "symbol": symbol}


async def get_watchlist_summary(db):
    """Get watchlist portfolio summary."""
    items = await get_watchlist_with_prices(db)

    total_invested = 0
    total_value = 0
    total_pnl = 0
    winners = 0
    losers = 0

    for item in items:
        if item.get("invested"):
            total_invested += item["invested"]
        if item.get("total_value"):
            total_value += item["total_value"]
        if item.get("total_pnl"):
            total_pnl += item["total_pnl"]
        if item.get("pnl_pct", 0) > 0:
            winners += 1
        elif item.get("pnl_pct", 0) < 0:
            losers += 1

    return {
        "total_stocks": len(items),
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_invested * 100), 2) if total_invested > 0 else 0,
        "winners": winners,
        "losers": losers,
        "items": items,
    }

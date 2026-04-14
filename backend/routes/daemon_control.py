"""Daemon control routes — pause/resume, status, kill switch."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daemon", tags=["daemon"])


@router.get("/status")
async def daemon_status(request: Request):
    """Get current daemon state."""
    from daemons.portfolio_daemon import daemon_state
    db = request.app.db
    config = await db.daemon_config.find_one({"type": "portfolio_daemon"}, {"_id": 0})
    paused = config.get("paused", False) if config else False

    return {
        "status": daemon_state["status"],
        "paused": paused,
        "last_action": daemon_state["last_action"],
        "last_action_at": daemon_state["last_action_at"],
        "cycle_count": daemon_state["cycle_count"],
        "recent_errors": daemon_state["errors"][-5:] if daemon_state["errors"] else [],
    }


@router.post("/toggle")
async def daemon_toggle(request: Request):
    """Toggle daemon pause/resume."""
    db = request.app.db
    config = await db.daemon_config.find_one({"type": "portfolio_daemon"})
    currently_paused = config.get("paused", False) if config else False
    new_state = not currently_paused

    await db.daemon_config.update_one(
        {"type": "portfolio_daemon"},
        {"$set": {"paused": new_state, "toggled_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    action = "paused" if new_state else "resumed"
    logger.info(f"DAEMON CONTROL: Portfolio daemon {action}")
    return {"paused": new_state, "action": action}

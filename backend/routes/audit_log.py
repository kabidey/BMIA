"""
Audit Log — Tracks every authenticated user action.
Middleware intercepts all API calls and logs: who, what, when, from where.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["audit"])

SUPERADMIN_EMAIL = "somnath.dey@smifs.com"

# Skip logging these noisy endpoints
SKIP_PATHS = {
    "/api/health", "/api/auth/session", "/api/market/cockpit",
    "/api/market/cockpit-slow", "/api/daemon/status",
}


async def audit_middleware(request: Request, call_next):
    """Middleware — logs every authenticated API request."""
    response = await call_next(request)

    path = request.url.path
    if path in SKIP_PATHS or not path.startswith("/api"):
        return response

    # Extract user from JWT
    auth = request.headers.get("Authorization", "")
    user_email = None
    user_name = None
    if auth.startswith("Bearer "):
        try:
            import jwt as pyjwt
            import os
            secret = os.environ.get("TOTP_JWT_SECRET", "bmia-jwt-secret")
            payload = pyjwt.decode(auth[7:], secret, algorithms=["HS256"])
            user_email = payload.get("sub")
            user_name = payload.get("name")
        except Exception:
            pass

    if not user_email and path not in {"/api/auth/check-email", "/api/auth/login", "/api/auth/set-password"}:
        return response

    # Build log entry
    method = request.method
    action = _describe_action(method, path)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_email": user_email or "anonymous",
        "user_name": user_name or "",
        "method": method,
        "path": path,
        "action": action,
        "status_code": response.status_code,
    }

    # Auth events get special logging
    if path == "/api/auth/check-email":
        entry["action"] = "Checked email access"
    elif path == "/api/auth/login":
        entry["action"] = "Logged in" if response.status_code == 200 else "Failed login"
    elif path == "/api/auth/set-password":
        entry["action"] = "Set new password"

    try:
        db = request.app.db
        await db.audit_log.insert_one(entry)
    except Exception as e:
        logger.debug(f"Audit log write failed: {e}")

    return response


def _describe_action(method, path):
    """Human-readable action description from method + path."""
    p = path.replace("/api/", "")

    if "portfolios/rebuild" in p:
        return "Triggered portfolio rebuild"
    if "portfolios/simulation" in p:
        return "Viewed portfolio simulation"
    if "portfolios/backtest" in p:
        return "Viewed portfolio backtest"
    if "portfolios/walk-forward" in p:
        return "Viewed walk-forward tracking"
    if "portfolios/analytics" in p:
        return "Viewed portfolio analytics"
    if "portfolios/overview" in p:
        return "Viewed portfolio overview"
    if "portfolios/rebalance" in p:
        return "Viewed rebalance log"
    if p.startswith("portfolios") and method == "POST":
        return "Constructed portfolio"

    if "custom-portfolios" in p:
        if method == "POST":
            return "Created custom portfolio"
        if method == "PUT":
            return "Rebalanced custom portfolio"
        if method == "DELETE":
            return "Deleted custom portfolio"
        return "Viewed custom portfolio"

    if "batch/god-scan" in p:
        return "Ran God Mode scan" if method == "POST" else "Checked scan status"
    if "batch/scan-history" in p:
        return "Viewed scan history"

    if "signals" in p:
        if "generate" in p:
            return "Generated signal"
        if "track-record" in p:
            return "Viewed track record"
        return "Viewed signals"

    if "analyze" in p or "analysis" in p:
        return "Analyzed symbol"
    if "symbols" in p:
        return "Searched symbols"
    if "guidance" in p:
        return "Viewed BSE guidance"
    if "market/session" in p:
        return "Checked market session"
    if "market/holidays" in p:
        return "Managed holidays"
    if "daemon" in p:
        return "Toggled daemon" if method == "POST" else "Checked daemon"
    if "audit" in p:
        return "Viewed audit log"

    return f"{method} {p}"


@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(default=100, le=500),
    user: str = Query(default=None),
    action: str = Query(default=None),
):
    """Get audit log entries. Superadmin only."""
    # Verify superadmin
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt as pyjwt
            import os
            secret = os.environ.get("TOTP_JWT_SECRET", "bmia-jwt-secret")
            payload = pyjwt.decode(auth[7:], secret, algorithms=["HS256"])
            if payload.get("sub") != SUPERADMIN_EMAIL:
                return {"logs": [], "total": 0, "error": "Superadmin access required"}
        except Exception:
            return {"logs": [], "total": 0, "error": "Invalid session"}
    else:
        return {"logs": [], "total": 0, "error": "Not authenticated"}

    db = request.app.db
    query = {}
    if user:
        query["user_email"] = {"$regex": user, "$options": "i"}
    if action:
        query["action"] = {"$regex": action, "$options": "i"}

    cursor = db.audit_log.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)

    # Get unique users for filter dropdown
    users = await db.audit_log.distinct("user_email")

    return {"logs": logs, "total": len(logs), "users": users}

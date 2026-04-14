"""
BMIA Authentication — OrgLens employee verification + local password auth.
Flow: Email → OrgLens scan (active employee?) → Password (set or verify) → JWT session.
Superadmin: somnath.dey@smifs.com (persistent session).
"""
import os
import logging
from datetime import datetime, timezone, timedelta

import jwt
import bcrypt
import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

APP_NAME = "BMIA"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 1
SUPERADMIN_EMAIL = "somnath.dey@smifs.com"
SUPERADMIN_JWT_DAYS = 365
ORGLENS_BASE = "https://orglens.pesmifs.com/api/v1"


def _jwt_secret():
    return os.environ.get("TOTP_JWT_SECRET", "bmia-jwt-secret")


def _orglens_key():
    return os.environ.get("ORGLENS_API_KEY", "")


# ── Request models ──

class EmailCheckReq(BaseModel):
    email: str

class LoginReq(BaseModel):
    email: str
    password: str

class SetPasswordReq(BaseModel):
    email: str
    password: str


# ── OrgLens verification ──

def _verify_orglens(email: str) -> dict:
    """Call OrgLens to check if email belongs to an active employee."""
    key = _orglens_key()
    if not key:
        return {"valid": False, "error": "OrgLens API key not configured"}
    try:
        res = requests.get(
            f"{ORGLENS_BASE}/employee/by-email/{email}",
            headers={"X-API-Key": key},
            timeout=10,
        )
        if res.status_code == 404:
            return {"valid": False, "error": "Not a registered employee"}
        if res.status_code == 200:
            emp = res.json().get("employee", {})
            status = emp.get("employment_status", "")
            if status != "Active":
                return {"valid": False, "error": f"Employee status: {status}"}
            return {
                "valid": True,
                "name": emp.get("name", ""),
                "department": emp.get("department", ""),
                "designation": emp.get("designation", ""),
                "email": email,
            }
        return {"valid": False, "error": f"OrgLens returned {res.status_code}"}
    except Exception as e:
        logger.error(f"OrgLens verification failed: {e}")
        return {"valid": False, "error": "OrgLens unreachable"}


# ── Endpoints ──

@router.post("/check-email")
async def check_email(req: EmailCheckReq, request: Request):
    """Step 1: User enters email. Verify via OrgLens, check if password exists."""
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")

    # Verify with OrgLens
    org = _verify_orglens(email)
    if not org["valid"]:
        raise HTTPException(status_code=403, detail=org.get("error", "Access denied"))

    # Check if user has a password set
    db = request.app.db
    user = await db.bmia_users.find_one({"email": email}, {"_id": 0, "email": 1})
    has_password = user is not None

    return {
        "status": "verified",
        "name": org.get("name", ""),
        "department": org.get("department", ""),
        "designation": org.get("designation", ""),
        "has_password": has_password,
        "is_superadmin": email == SUPERADMIN_EMAIL,
    }


@router.post("/set-password")
async def set_password(req: SetPasswordReq, request: Request):
    """Step 2a: New user sets their password."""
    email = req.email.strip().lower()
    password = req.password

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Verify with OrgLens first
    org = _verify_orglens(email)
    if not org["valid"]:
        raise HTTPException(status_code=403, detail=org.get("error", "Access denied"))

    db = request.app.db
    existing = await db.bmia_users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Password already set. Use login.")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
    await db.bmia_users.insert_one({
        "email": email,
        "password_hash": hashed,
        "name": org.get("name", ""),
        "department": org.get("department", ""),
        "designation": org.get("designation", ""),
        "is_superadmin": email == SUPERADMIN_EMAIL,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(f"New user registered: {email}")
    return {"status": "password_set"}


@router.post("/login")
async def login(req: LoginReq, request: Request):
    """Step 2b: Existing user logs in with password."""
    email = req.email.strip().lower()
    password = req.password

    # Verify with OrgLens — must still be active
    org = _verify_orglens(email)
    if not org["valid"]:
        raise HTTPException(status_code=403, detail=org.get("error", "Access denied"))

    db = request.app.db
    user = await db.bmia_users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="No account found. Set a password first.")

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Issue JWT
    is_super = email == SUPERADMIN_EMAIL
    expiry = timedelta(days=SUPERADMIN_JWT_DAYS) if is_super else timedelta(hours=JWT_EXPIRY_HOURS)

    payload = {
        "iss": APP_NAME,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expiry,
        "sub": email,
        "name": org.get("name", user.get("name", "")),
        "department": org.get("department", ""),
        "designation": org.get("designation", ""),
        "superadmin": is_super,
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)

    logger.info(f"Login: {email} ({'superadmin' if is_super else '1h session'})")
    return {
        "status": "authenticated",
        "token": token,
        "name": payload["name"],
        "email": email,
        "department": payload["department"],
        "designation": payload["designation"],
        "superadmin": is_super,
        "expires_in": int(expiry.total_seconds()),
    }


@router.get("/session")
async def check_session(request: Request):
    """Check if the current JWT session is valid."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return {"valid": False}

    token = auth[7:]
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        return {
            "valid": True,
            "email": payload.get("sub"),
            "name": payload.get("name"),
            "department": payload.get("department"),
            "designation": payload.get("designation"),
            "superadmin": payload.get("superadmin", False),
            "exp": payload.get("exp"),
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "reason": "expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "reason": "invalid"}

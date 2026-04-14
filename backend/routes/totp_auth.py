"""TOTP Authentication — RFC 6238 + Master Code with persistent session.
Master code is bcrypt-hashed in MongoDB, never stored in plaintext.
"""
import os
import logging
from datetime import datetime, timezone, timedelta

import jwt
import pyotp
import bcrypt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

APP_NAME = "BMIA"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 1
MASTER_JWT_EXPIRY_DAYS = 365


def _get_jwt_secret():
    return os.environ.get("TOTP_JWT_SECRET", "bmia-totp-jwt-secret-change-me")


class VerifyRequest(BaseModel):
    code: str


@router.get("/totp-setup")
async def totp_setup(request: Request):
    """Ensures TOTP is ready. Seeds master code hash if not present."""
    secret = os.environ.get("TOTP_SECRET")
    if not secret:
        return {"status": "error", "detail": "TOTP_SECRET not configured"}

    # Seed master code hash if not in DB yet
    db = request.app.db
    existing = await db.auth_config.find_one({"type": "master_code"})
    if not existing:
        master_plain = os.environ.get("MASTER_CODE", "")
        if master_plain:
            hashed = bcrypt.hashpw(master_plain.encode(), bcrypt.gensalt(12)).decode()
            await db.auth_config.insert_one({
                "type": "master_code",
                "hash": hashed,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info("Master code seeded (bcrypt hash stored)")

    return {"status": "ready"}


@router.post("/totp-verify")
async def totp_verify(req: VerifyRequest, request: Request):
    """Verify TOTP or master code. Master code gives persistent session."""
    db = request.app.db
    code = req.code.strip()

    # Check master code first
    master_doc = await db.auth_config.find_one({"type": "master_code"}, {"_id": 0})
    if master_doc and master_doc.get("hash"):
        if bcrypt.checkpw(code.encode(), master_doc["hash"].encode()):
            jwt_secret = _get_jwt_secret()
            payload = {
                "iss": APP_NAME,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(days=MASTER_JWT_EXPIRY_DAYS),
                "sub": "master",
                "persistent": True,
            }
            token = jwt.encode(payload, jwt_secret, algorithm=JWT_ALGORITHM)
            logger.info("Master code verified — persistent session issued")
            return {
                "status": "verified",
                "token": token,
                "expires_in": MASTER_JWT_EXPIRY_DAYS * 86400,
                "persistent": True,
            }

    # Regular TOTP
    secret = os.environ.get("TOTP_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="TOTP_SECRET not configured")

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        logger.warning("TOTP verification failed")
        raise HTTPException(status_code=401, detail="Invalid code. Try again.")

    jwt_secret = _get_jwt_secret()
    payload = {
        "iss": APP_NAME,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "sub": "admin",
    }
    token = jwt.encode(payload, jwt_secret, algorithm=JWT_ALGORITHM)

    logger.info("TOTP verification successful — 1h session issued")
    return {
        "status": "verified",
        "token": token,
        "expires_in": JWT_EXPIRY_HOURS * 3600,
    }


@router.get("/session")
async def check_session(request: Request):
    """Check if the current session token is valid."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"valid": False}

    token = auth_header[7:]
    jwt_secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])
        return {
            "valid": True,
            "sub": payload.get("sub"),
            "exp": payload.get("exp"),
            "persistent": payload.get("persistent", False),
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "reason": "expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "reason": "invalid"}

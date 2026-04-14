"""TOTP Authentication — RFC 6238 Time-based One-Time Password.
Compatible with Google Authenticator, Authy, Microsoft Authenticator.
"""
import os
import io
import time
import base64
import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta

import jwt
import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

APP_NAME = "BMIA"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 1


def _get_jwt_secret(db=None):
    return os.environ.get("TOTP_JWT_SECRET", "bmia-totp-jwt-secret-change-me")


class VerifyRequest(BaseModel):
    code: str


@router.get("/totp-setup")
async def totp_setup(request: Request):
    """Ensures TOTP is ready. Secret comes from TOTP_SECRET env var."""
    secret = os.environ.get("TOTP_SECRET")
    if not secret:
        return {"status": "error", "detail": "TOTP_SECRET not configured in environment"}
    return {"status": "ready"}


@router.post("/totp-verify")
async def totp_verify(req: VerifyRequest, request: Request):
    """Verify a 6-digit TOTP code and return a JWT session token."""
    secret = os.environ.get("TOTP_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="TOTP_SECRET not configured")

    totp = pyotp.TOTP(secret)

    if not totp.verify(req.code, valid_window=1):
        logger.warning(f"TOTP verification failed")
        raise HTTPException(status_code=401, detail="Invalid code. Try again.")

    # Issue JWT
    jwt_secret = _get_jwt_secret()
    payload = {
        "iss": APP_NAME,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "sub": "admin",
    }
    token = jwt.encode(payload, jwt_secret, algorithm=JWT_ALGORITHM)

    logger.info("TOTP verification successful — session issued")
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
        return {"valid": True, "sub": payload.get("sub"), "exp": payload.get("exp")}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "reason": "expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "reason": "invalid"}

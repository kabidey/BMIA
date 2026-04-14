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
    """Get QR code for TOTP setup. Creates secret if not exists."""
    db = request.app.db
    config = await db.auth_config.find_one({"type": "totp"}, {"_id": 0})

    if not config:
        # Generate new TOTP secret
        secret = pyotp.random_base32()
        await db.auth_config.insert_one({
            "type": "totp",
            "secret": secret,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "setup_complete": False,
        })
    else:
        secret = config["secret"]

    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name="admin", issuer_name=APP_NAME)

    img = qrcode.make(provisioning_uri, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "qr_code": f"data:image/png;base64,{qr_b64}",
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "setup_complete": config.get("setup_complete", False) if config else False,
    }


@router.post("/totp-verify")
async def totp_verify(req: VerifyRequest, request: Request):
    """Verify a 6-digit TOTP code and return a JWT session token."""
    db = request.app.db
    config = await db.auth_config.find_one({"type": "totp"}, {"_id": 0})

    if not config:
        raise HTTPException(status_code=400, detail="TOTP not configured. Visit /api/auth/totp-setup first.")

    secret = config["secret"]
    totp = pyotp.TOTP(secret)

    # Verify with ±1 window tolerance (60s total — handles slight clock drift)
    if not totp.verify(req.code, valid_window=1):
        logger.warning(f"TOTP verification failed for code: {req.code[:2]}****")
        raise HTTPException(status_code=401, detail="Invalid code. Try again.")

    # Mark setup as complete on first successful verify
    if not config.get("setup_complete"):
        await db.auth_config.update_one(
            {"type": "totp"},
            {"$set": {"setup_complete": True}}
        )

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

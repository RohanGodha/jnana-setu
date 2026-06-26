"""JWT auth + password hashing + FastAPI dependencies.

- Passwords hashed with bcrypt (passlib).
- JWT (HS256) with configurable expiry.
- ``current_user`` dependency validates the bearer token.
- ``enforce_query_limit`` applies the free-tier daily quota and returns the
  user's usage for the response.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt

import db
from config import settings

_bearer = HTTPBearer(auto_error=False)

TIER_DAILY_LIMITS = {
    "free": settings.free_tier_daily_limit,
    "premium": 10_000,
    "scholar": 10_000,
    "institutional": 1_000_000,
}


def _pw_bytes(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes; truncate explicitly to avoid errors.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode(creds.credentials)
    user = db.get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def is_admin(user: dict) -> bool:
    admin = (settings.admin_email or "").strip().lower()
    return bool(admin) and user.get("email", "").lower() == admin


def has_unlimited(user: dict) -> bool:
    """Admins and users with an active Pro subscription have unlimited access."""
    return is_admin(user) or db.pro_active(user)


def daily_limit_for(tier: str) -> int:
    return TIER_DAILY_LIMITS.get(tier, settings.free_tier_daily_limit)


def effective_limit(user: dict) -> int:
    if has_unlimited(user):
        return 1_000_000
    return daily_limit_for(user["tier"])


def require_admin(user: dict = Depends(current_user)) -> dict:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def enforce_query_limit(user: dict) -> None:
    """Raise 429 if a free-tier user has hit the daily quota. Admins and active
    Pro users bypass the limit entirely."""
    if has_unlimited(user):
        return
    limit = daily_limit_for(user["tier"])
    used = db.queries_today(user["id"])
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily limit reached. Upgrade to Pro for unlimited access.",
        )


def enforce_hindi_access(user: dict, language: str) -> None:
    if language == "hi" and user["tier"] == "free" and not has_unlimited(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hindi responses require Pro.",
        )

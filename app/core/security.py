from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import uuid

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException

settings = get_settings()

# Configure Passlib with Argon2 (fallback to bcrypt if needed)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashes plain text password using Argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain text password against Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates short-lived JWT Access Token (default 15 minutes)."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "role": role,
        "token_type": "access",
        "jti": jti,
        "exp": expire,
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: uuid.UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str, int]:
    """
    Generates long-lived JWT Refresh Token (default 7 days).
    Returns tuple: (token_str, jti_str, expires_in_seconds)
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    expires_in_seconds = int((expire - now).total_seconds())

    payload = {
        "sub": str(user_id),
        "role": role,
        "token_type": "refresh",
        "jti": jti,
        "exp": expire,
        "iat": now,
    }

    token = jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_in_seconds


def decode_token(token: str, is_refresh: bool = False) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Raises UnauthorizedException on invalid signature or expiration.
    """
    secret = settings.JWT_REFRESH_SECRET if is_refresh else settings.JWT_SECRET_KEY
    expected_type = "refresh" if is_refresh else "access"

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("token_type") != expected_type:
            raise UnauthorizedException(
                message=f"Invalid token type. Expected '{expected_type}'",
                details={"token_type": payload.get("token_type")},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message="Token has expired")
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException(message=f"Invalid token: {str(exc)}")

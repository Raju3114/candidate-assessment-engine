from typing import Callable, List
import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.models.user import User, UserRole
from app.repositories.user_repository import SQLAlchemyUserRepository

security_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> tuple[User, dict]:
    """
    Decodes HTTP Bearer JWT token, verifies Redis blacklist status, and loads current user.
    Returns tuple of (User entity, token_payload dictionary).
    """
    token = credentials.credentials
    payload = decode_token(token, is_refresh=False)
    jti = payload.get("jti")
    user_id_str = payload.get("sub")

    if not user_id_str or not jti:
        raise UnauthorizedException(message="Invalid token claims")

    # Check Redis Access Token Blacklist
    is_blacklisted = await redis.get(f"blacklist:token:{jti}")
    if is_blacklisted:
        raise UnauthorizedException(message="Access token has been revoked")

    user_repo = SQLAlchemyUserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id_str))

    if not user:
        raise UnauthorizedException(message="User associated with token no longer exists")

    return user, payload


async def get_current_active_user(
    user_data: tuple[User, dict] = Depends(get_current_user),
) -> User:
    """Verifies that the current user is active."""
    user, _ = user_data
    if not user.is_active:
        raise ForbiddenException(message="User account is inactive")
    return user


def role_required(allowed_roles: List[UserRole]) -> Callable:
    """
    Dependency factory enforcing Role-Based Access Control (RBAC).
    Usage: Depends(role_required([UserRole.RECRUITER, UserRole.ADMIN]))
    """

    async def role_checker(user_data: tuple[User, dict] = Depends(get_current_user)) -> User:
        user, _ = user_data
        if not user.is_active:
            raise ForbiddenException(message="User account is inactive")
        if user.role not in allowed_roles:
            raise ForbiddenException(
                message=f"Action requires one of the following roles: {[r.value for r in allowed_roles]}"
            )
        return user

    return role_checker

import logging
from typing import Optional
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import IUserRepository, SQLAlchemyUserRepository
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """Service handling user registration, authentication, token rotation, and logouts."""

    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db_session = db_session
        self.redis = redis_client
        self.user_repo: IUserRepository = SQLAlchemyUserRepository(db_session)

    async def register_user(self, payload: UserCreate) -> tuple[UserResponse, TokenResponse]:
        """Registers a new user account and returns the user object with initial tokens."""
        existing_user = await self.user_repo.get_by_email(payload.email)
        if existing_user:
            raise ConflictException(message="A user with this email address already exists")

        hashed_pwd = hash_password(payload.password)
        new_user = User(
            email=payload.email.lower(),
            hashed_password=hashed_pwd,
            role=payload.role,
            first_name=payload.first_name,
            last_name=payload.last_name,
            is_active=True,
            is_verified=False,
        )

        user = await self.user_repo.create(new_user)
        await self.user_repo.update_last_login(user.id)
        await self.db_session.commit()

        # Issue token pair
        tokens = await self._issue_token_pair(user)
        user_response = UserResponse.model_validate(user)

        return user_response, tokens

    async def login_user(self, payload: UserLogin) -> tuple[UserResponse, TokenResponse]:
        """Authenticates user credentials and issues a fresh token pair."""
        user = await self.user_repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException(message="Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException(message="User account is disabled")

        await self.user_repo.update_last_login(user.id)
        await self.db_session.commit()

        tokens = await self._issue_token_pair(user)
        user_response = UserResponse.model_validate(user)

        return user_response, tokens

    async def refresh_access_token(self, refresh_token_str: str) -> TokenResponse:
        """
        Validates refresh token, enforces token rotation, and issues a new token pair.
        """
        payload = decode_token(refresh_token_str, is_refresh=True)
        user_id_str = payload.get("sub")
        old_jti = payload.get("jti")

        if not user_id_str or not old_jti:
            raise UnauthorizedException(message="Invalid token claims")

        user_id = uuid.UUID(user_id_str)
        redis_key = f"refresh_token:{user_id_str}:{old_jti}"

        # Verify refresh token exists in Redis
        stored_token = await self.redis.get(redis_key)
        if not stored_token:
            raise UnauthorizedException(message="Refresh token has been revoked or expired")

        # Invalidate old refresh token (Token Rotation)
        await self.redis.delete(redis_key)

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException(message="User account disabled or not found")

        # Issue new token pair
        return await self._issue_token_pair(user)

    async def logout_user(self, access_token_jti: str, access_token_ttl: int, user_id: uuid.UUID) -> None:
        """
        Blacklists current access token and clears all active refresh tokens for the user in Redis.
        """
        # 1. Blacklist access token
        if access_token_ttl > 0:
            await self.redis.setex(f"blacklist:token:{access_token_jti}", access_token_ttl, "revoked")

        # 2. Revoke user refresh tokens
        pattern = f"refresh_token:{str(user_id)}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def _issue_token_pair(self, user: User) -> TokenResponse:
        """Private helper to generate access/refresh tokens and store refresh token JTI in Redis."""
        access_token = create_access_token(user_id=user.id, role=user.role.value)
        refresh_token, jti, ttl_seconds = create_refresh_token(user_id=user.id, role=user.role.value)

        # Store refresh token JTI in Redis with TTL
        redis_key = f"refresh_token:{str(user.id)}:{jti}"
        await self.redis.setex(redis_key, ttl_seconds, "active")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

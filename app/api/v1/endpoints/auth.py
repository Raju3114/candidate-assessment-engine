from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.responses import ApiResponse
from app.core.security_brute_force import BruteForceProtector
from app.dependencies.auth import get_current_active_user, get_current_user
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication & Authorization"])


class AuthRegisterResponseData(UserResponse):
    tokens: TokenResponse


@router.post(
    "/register",
    response_model=ApiResponse[AuthRegisterResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Registers a new candidate or recruiter account and returns user details with initial access & refresh token pair.",
)
async def register(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[AuthRegisterResponseData]:
    service = AuthService(db, redis)
    user_data, tokens = await service.register_user(payload)

    # Record Audit Event
    audit_svc = AuditService(db)
    ip_address = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent")
    await audit_svc.log_event("USER_REGISTER", f"/auth/register?role={payload.role.value}", user_id=user_data.id, ip_address=ip_address, user_agent=user_agent)

    response_payload = AuthRegisterResponseData(
        **user_data.model_dump(),
        tokens=tokens,
    )
    return ApiResponse.ok(response_payload)


@router.post(
    "/login",
    response_model=ApiResponse[AuthRegisterResponseData],
    status_code=status.HTTP_200_OK,
    summary="User Authentication Login",
    description="Authenticates credentials against Argon2id hash with brute force lockout protection.",
)
async def login(
    payload: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[AuthRegisterResponseData]:
    ip_address = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent")
    protector = BruteForceProtector(redis)

    # 1. Check Brute Force Lockout
    await protector.check_lockout(ip_address, payload.email)

    service = AuthService(db, redis)
    audit_svc = AuditService(db)

    try:
        user_data, tokens = await service.login_user(payload)
        # Reset failed attempts on success
        await protector.reset_failed_attempts(ip_address, payload.email)
        await audit_svc.log_event("USER_LOGIN_SUCCESS", "/auth/login", user_id=user_data.id, ip_address=ip_address, user_agent=user_agent)

        response_payload = AuthRegisterResponseData(
            **user_data.model_dump(),
            tokens=tokens,
        )
        return ApiResponse.ok(response_payload)

    except UnauthorizedException as exc:
        # Record failed login attempt for lockout tracking
        await protector.record_failed_attempt(ip_address, payload.email)
        await audit_svc.log_event("USER_LOGIN_FAILED", f"/auth/login?email={payload.email}", ip_address=ip_address, user_agent=user_agent)
        raise exc


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token (Token Rotation)",
    description="Validates an active JWT Refresh Token, invalidates it in Redis, and issues a new token pair.",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[TokenResponse]:
    service = AuthService(db, redis)
    tokens = await service.refresh_access_token(payload.refresh_token)
    return ApiResponse.ok(tokens)


@router.post(
    "/logout",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="User Logout & Token Revocation",
    description="Blacklists current access token JTI and revokes all active refresh tokens in Redis.",
)
async def logout(
    request: Request,
    user_data: tuple[User, dict] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[dict]:
    user, payload = user_data
    jti = payload.get("jti")
    exp = payload.get("exp")
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(0, exp - now) if exp else 0

    service = AuthService(db, redis)
    await service.logout_user(
        access_token_jti=jti,
        access_token_ttl=ttl,
        user_id=user.id,
    )

    audit_svc = AuditService(db)
    ip_address = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent")
    await audit_svc.log_event("USER_LOGOUT", "/auth/logout", user_id=user.id, ip_address=ip_address, user_agent=user_agent)

    return ApiResponse.ok({"message": "Successfully logged out and tokens revoked"})


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns authenticated user profile details.",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> ApiResponse[UserResponse]:
    user_response = UserResponse.model_validate(current_user)
    return ApiResponse.ok(user_response)

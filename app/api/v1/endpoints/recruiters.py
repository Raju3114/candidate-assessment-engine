import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse
from app.dependencies.auth import role_required
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.profile import RecruiterCreate, RecruiterResponse, RecruiterUpdate
from app.services.recruiter_service import RecruiterService

router = APIRouter(prefix="/recruiters", tags=["Recruiter Profiles"])


@router.post(
    "/profile",
    response_model=ApiResponse[RecruiterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Recruiter Profile",
    description="Creates a recruiter profile for the authenticated RECRUITER user.",
)
async def create_recruiter_profile(
    payload: RecruiterCreate,
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecruiterResponse]:
    service = RecruiterService(db)
    profile = await service.create_profile(user, payload)
    return ApiResponse.ok(profile)


@router.get(
    "/me",
    response_model=ApiResponse[RecruiterResponse],
    status_code=status.HTTP_200_OK,
    summary="Get My Recruiter Profile",
    description="Returns recruiter profile of the authenticated RECRUITER user.",
)
async def get_my_recruiter_profile(
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecruiterResponse]:
    service = RecruiterService(db)
    profile = await service.get_profile_by_user_id(user.id)
    return ApiResponse.ok(profile)


@router.put(
    "/me",
    response_model=ApiResponse[RecruiterResponse],
    status_code=status.HTTP_200_OK,
    summary="Update My Recruiter Profile",
    description="Updates recruiter profile fields for the authenticated RECRUITER user.",
)
async def update_my_recruiter_profile(
    payload: RecruiterUpdate,
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecruiterResponse]:
    service = RecruiterService(db)
    profile = await service.update_profile(user, payload)
    return ApiResponse.ok(profile)


@router.get(
    "/{recruiter_id}",
    response_model=ApiResponse[RecruiterResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Recruiter Profile by ID",
    description="Allows ADMIN and CANDIDATE users to fetch recruiter profile details by recruiter UUID.",
)
async def get_recruiter_by_id(
    recruiter_id: uuid.UUID,
    user: User = Depends(role_required([UserRole.ADMIN, UserRole.CANDIDATE, UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RecruiterResponse]:
    service = RecruiterService(db)
    profile = await service.get_profile_by_id(recruiter_id)
    return ApiResponse.ok(profile)

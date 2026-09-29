from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse
from app.dependencies.auth import get_current_user, role_required
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.profile import CandidateCreate, CandidateResponse, CandidateUpdate
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/candidates", tags=["Candidate Profiles"])


@router.post(
    "/profile",
    response_model=ApiResponse[CandidateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Candidate Profile",
    description="Creates a detailed candidate profile for the authenticated CANDIDATE user.",
)
async def create_candidate_profile(
    payload: CandidateCreate,
    user: User = Depends(role_required([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CandidateResponse]:
    service = CandidateService(db)
    profile = await service.create_profile(user, payload)
    return ApiResponse.ok(profile)


@router.get(
    "/me",
    response_model=ApiResponse[CandidateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get My Candidate Profile",
    description="Returns candidate profile of the authenticated CANDIDATE user.",
)
async def get_my_candidate_profile(
    user: User = Depends(role_required([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CandidateResponse]:
    service = CandidateService(db)
    profile = await service.get_profile_by_user_id(user.id)
    return ApiResponse.ok(profile)


@router.put(
    "/me",
    response_model=ApiResponse[CandidateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update My Candidate Profile",
    description="Updates candidate profile fields for the authenticated CANDIDATE user.",
)
async def update_my_candidate_profile(
    payload: CandidateUpdate,
    user: User = Depends(role_required([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CandidateResponse]:
    service = CandidateService(db)
    profile = await service.update_profile(user, payload)
    return ApiResponse.ok(profile)


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[CandidateResponse]],
    status_code=status.HTTP_200_OK,
    summary="Search & Filter Candidates",
    description="Allows RECRUITER and ADMIN users to search candidate profiles by skill tag and experience range with pagination.",
)
async def search_candidates(
    skill: Optional[str] = Query(None, description="Skill tag filter e.g. Python, SQL"),
    min_experience: Optional[float] = Query(None, ge=0.0, description="Minimum experience years filter"),
    max_experience: Optional[float] = Query(None, ge=0.0, description="Maximum experience years filter"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Page size limit"),
    user: User = Depends(role_required([UserRole.RECRUITER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[CandidateResponse]]:
    service = CandidateService(db)
    result = await service.search_candidates(
        skill=skill,
        min_experience=min_experience,
        max_experience=max_experience,
        page=page,
        size=size,
    )
    return ApiResponse.ok(result)


@router.get(
    "/{candidate_id}",
    response_model=ApiResponse[CandidateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Candidate Profile by ID",
    description="Allows RECRUITER and ADMIN users to fetch candidate profile details by candidate UUID.",
)
async def get_candidate_by_id(
    candidate_id: uuid.UUID,
    user: User = Depends(role_required([UserRole.RECRUITER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CandidateResponse]:
    service = CandidateService(db)
    profile = await service.get_profile_by_id(candidate_id)
    return ApiResponse.ok(profile)

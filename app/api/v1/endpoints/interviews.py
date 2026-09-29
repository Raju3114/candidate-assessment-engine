from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse
from app.dependencies.auth import get_current_active_user, role_required
from app.dependencies.database import get_db
from app.models.interview import InterviewStatus, InterviewType
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewSchedule,
)
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["Interview Session Management"])


@router.post(
    "",
    response_model=ApiResponse[InterviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Interview Session",
    description="Creates a new interview session in DRAFT or SCHEDULED state for an assigned candidate.",
)
async def create_interview(
    payload: InterviewCreate,
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InterviewResponse]:
    service = InterviewService(db)
    session = await service.create_interview(user, payload)
    return ApiResponse.ok(session)


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[InterviewResponse]],
    status_code=status.HTTP_200_OK,
    summary="List & Filter Interview Sessions",
    description="Returns a paginated list of interview sessions filtered by status, candidate, recruiter, or date range.",
)
async def list_interviews(
    status_filter: Optional[InterviewStatus] = Query(None, alias="status", description="Filter by lifecycle status"),
    candidate_id: Optional[uuid.UUID] = Query(None, description="Filter by candidate UUID"),
    recruiter_id: Optional[uuid.UUID] = Query(None, description="Filter by recruiter UUID"),
    interview_type: Optional[InterviewType] = Query(None, description="Filter by interview category"),
    start_date: Optional[datetime] = Query(None, description="Filter scheduled at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter scheduled at <= end_date"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page limit size"),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[InterviewResponse]]:
    service = InterviewService(db)
    result = await service.list_interviews(
        user=user,
        status=status_filter,
        candidate_id=candidate_id,
        recruiter_id=recruiter_id,
        interview_type=interview_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        size=size,
    )
    return ApiResponse.ok(result)


@router.get(
    "/{interview_id}",
    response_model=ApiResponse[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Interview Session Details",
    description="Fetches detailed metadata of an interview session by UUID.",
)
async def get_interview_details(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InterviewResponse]:
    service = InterviewService(db)
    session = await service.get_interview_details(user, interview_id)
    return ApiResponse.ok(session)


@router.patch(
    "/{interview_id}/schedule",
    response_model=ApiResponse[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Schedule Interview Session",
    description="Schedules or reschedules an interview session timestamp.",
)
async def schedule_interview(
    interview_id: uuid.UUID,
    payload: InterviewSchedule,
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InterviewResponse]:
    service = InterviewService(db)
    session = await service.schedule_interview(user, interview_id, payload)
    return ApiResponse.ok(session)


@router.patch(
    "/{interview_id}/start",
    response_model=ApiResponse[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Start Interview Session",
    description="Transitions an interview session from SCHEDULED to IN_PROGRESS state.",
)
async def start_interview(
    interview_id: uuid.UUID,
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InterviewResponse]:
    service = InterviewService(db)
    session = await service.start_interview(user, interview_id)
    return ApiResponse.ok(session)


@router.patch(
    "/{interview_id}/complete",
    response_model=ApiResponse[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Complete Interview Session",
    description="Transitions an IN_PROGRESS interview session to COMPLETED state.",
)
async def complete_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InterviewResponse]:
    service = InterviewService(db)
    session = await service.complete_interview(user, interview_id)
    return ApiResponse.ok(session)


@router.patch(
    "/{interview_id}/cancel",
    response_model=ApiResponse[InterviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel Interview Session",
    description="Cancels an interview session.",
)
async def cancel_interview(
    interview_id: uuid.UUID,
    user: User = Depends(role_required([UserRole.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InterviewResponse]:
    service = InterviewService(db)
    session = await service.cancel_interview(user, interview_id)
    return ApiResponse.ok(session)

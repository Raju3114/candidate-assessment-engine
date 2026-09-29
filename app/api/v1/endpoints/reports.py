import uuid

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse
from app.dependencies.auth import get_current_active_user, role_required
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.models.user import User, UserRole
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(tags=["Final Reports & Analytics Engine"])


@router.post(
    "/interviews/{interview_id}/generate-report",
    response_model=ApiResponse[ReportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Final Interview Report",
    description="Aggregates all answer evaluations, calculates skill category analytics, computes hiring recommendation, and generates executive summary report.",
)
async def generate_interview_report(
    interview_id: uuid.UUID,
    user: User = Depends(role_required([UserRole.RECRUITER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[ReportResponse]:
    service = ReportService(db, redis)
    report = await service.generate_report(user, interview_id)
    return ApiResponse.ok(report)


@router.get(
    "/interviews/{interview_id}/report",
    response_model=ApiResponse[ReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Interview Final Report",
    description="Fetches final interview report and analytics breakdown with Redis cache-aside support.",
)
async def get_interview_report(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[ReportResponse]:
    service = ReportService(db, redis)
    report = await service.get_report_by_interview(user, interview_id)
    return ApiResponse.ok(report)


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[ReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Report by ID",
    description="Fetches a final report by report UUID primary key.",
)
async def get_report_by_id(
    report_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[ReportResponse]:
    service = ReportService(db, redis)
    report = await service.get_report_by_id(user, report_id)
    return ApiResponse.ok(report)

from datetime import datetime, timezone
import math
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.interview import InterviewSession, InterviewStatus, InterviewType
from app.models.user import User, UserRole
from app.repositories.candidate_repository import SQLAlchemyCandidateRepository
from app.repositories.interview_repository import IInterviewRepository, SQLAlchemyInterviewRepository
from app.repositories.recruiter_repository import SQLAlchemyRecruiterRepository
from app.schemas.common import PaginatedResponse
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewSchedule,
    InterviewUpdate,
)


class InterviewService:
    """Service handling lifecycle state transitions and access control for interview sessions."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.interview_repo: IInterviewRepository = SQLAlchemyInterviewRepository(db_session)
        self.candidate_repo = SQLAlchemyCandidateRepository(db_session)
        self.recruiter_repo = SQLAlchemyRecruiterRepository(db_session)

    async def create_interview(self, user: User, payload: InterviewCreate) -> InterviewResponse:
        if user.role != UserRole.RECRUITER and user.role != UserRole.ADMIN:
            raise ForbiddenException(message="Only recruiters can create interview sessions")

        recruiter = await self.recruiter_repo.get_by_user_id(user.id)
        if not recruiter:
            raise NotFoundException(message="Recruiter profile not found. Please create a recruiter profile first.")

        candidate = await self.candidate_repo.get_by_id(payload.candidate_id)
        if not candidate:
            raise NotFoundException(message=f"Candidate profile with ID '{payload.candidate_id}' not found")

        initial_status = InterviewStatus.SCHEDULED if payload.scheduled_at else InterviewStatus.DRAFT

        session = InterviewSession(
            recruiter_id=recruiter.id,
            candidate_id=candidate.id,
            title=payload.title,
            target_role=payload.target_role,
            experience_level=payload.experience_level,
            interview_type=payload.interview_type,
            status=initial_status,
            duration_minutes=payload.duration_minutes,
            scheduled_at=payload.scheduled_at,
            created_by=user.id,
            updated_by=user.id,
        )

        created = await self.interview_repo.create(session)
        await self.db_session.commit()
        return InterviewResponse.model_validate(created)

    async def get_interview_details(self, user: User, session_id: uuid.UUID) -> InterviewResponse:
        session = await self.interview_repo.get_by_id(session_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{session_id}' not found")

        await self._verify_session_access(user, session)
        return InterviewResponse.model_validate(session)

    async def schedule_interview(
        self, user: User, session_id: uuid.UUID, payload: InterviewSchedule
    ) -> InterviewResponse:
        session = await self.interview_repo.get_by_id(session_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{session_id}' not found")

        await self._verify_recruiter_ownership(user, session)

        if session.status in [InterviewStatus.COMPLETED, InterviewStatus.CANCELLED]:
            raise BadRequestException(message=f"Cannot schedule an interview in '{session.status}' status")

        session.scheduled_at = payload.scheduled_at
        session.status = InterviewStatus.SCHEDULED
        session.updated_by = user.id

        updated = await self.interview_repo.update(session)
        await self.db_session.commit()
        return InterviewResponse.model_validate(updated)

    async def start_interview(self, user: User, session_id: uuid.UUID) -> InterviewResponse:
        session = await self.interview_repo.get_by_id(session_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{session_id}' not found")

        await self._verify_recruiter_ownership(user, session)

        if session.status == InterviewStatus.CANCELLED:
            raise BadRequestException(message="Cancelled interviews cannot be started")
        if session.status == InterviewStatus.COMPLETED:
            raise BadRequestException(message="Completed interviews cannot be restarted")

        session.status = InterviewStatus.IN_PROGRESS
        session.started_at = datetime.now(timezone.utc)
        session.updated_by = user.id

        updated = await self.interview_repo.update(session)
        await self.db_session.commit()
        return InterviewResponse.model_validate(updated)

    async def complete_interview(self, user: User, session_id: uuid.UUID) -> InterviewResponse:
        session = await self.interview_repo.get_by_id(session_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{session_id}' not found")

        await self._verify_session_access(user, session)

        if session.status != InterviewStatus.IN_PROGRESS:
            raise BadRequestException(
                message=f"Only IN_PROGRESS interviews can be completed (current status: '{session.status}')"
            )

        session.status = InterviewStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        session.updated_by = user.id

        updated = await self.interview_repo.update(session)
        await self.db_session.commit()
        return InterviewResponse.model_validate(updated)

    async def cancel_interview(self, user: User, session_id: uuid.UUID) -> InterviewResponse:
        session = await self.interview_repo.get_by_id(session_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{session_id}' not found")

        await self._verify_recruiter_ownership(user, session)

        if session.status == InterviewStatus.COMPLETED:
            raise BadRequestException(message="Completed interviews cannot be cancelled")

        session.status = InterviewStatus.CANCELLED
        session.updated_by = user.id

        updated = await self.interview_repo.update(session)
        await self.db_session.commit()
        return InterviewResponse.model_validate(updated)

    async def list_interviews(
        self,
        user: User,
        status: Optional[InterviewStatus] = None,
        candidate_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        interview_type: Optional[InterviewType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[InterviewResponse]:
        page = max(1, page)
        size = min(max(1, size), 100)
        offset = (page - 1) * size

        # Role-based scoping
        if user.role == UserRole.CANDIDATE:
            candidate = await self.candidate_repo.get_by_user_id(user.id)
            candidate_id = candidate.id if candidate else uuid.uuid4()
        elif user.role == UserRole.RECRUITER:
            recruiter = await self.recruiter_repo.get_by_user_id(user.id)
            recruiter_id = recruiter.id if recruiter else uuid.uuid4()

        sessions, total = await self.interview_repo.list_filtered(
            status=status,
            candidate_id=candidate_id,
            recruiter_id=recruiter_id,
            interview_type=interview_type,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=size,
        )

        items = [InterviewResponse.model_validate(s) for s in sessions]
        pages = math.ceil(total / size) if size > 0 else 0

        return PaginatedResponse[InterviewResponse](
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def _verify_recruiter_ownership(self, user: User, session: InterviewSession) -> None:
        if user.role == UserRole.ADMIN:
            return
        recruiter = await self.recruiter_repo.get_by_user_id(user.id)
        if not recruiter or session.recruiter_id != recruiter.id:
            raise ForbiddenException(message="You do not have permission to modify this interview session")

    async def _verify_session_access(self, user: User, session: InterviewSession) -> None:
        if user.role == UserRole.ADMIN:
            return
        if user.role == UserRole.RECRUITER:
            recruiter = await self.recruiter_repo.get_by_user_id(user.id)
            if recruiter and session.recruiter_id == recruiter.id:
                return
        elif user.role == UserRole.CANDIDATE:
            candidate = await self.candidate_repo.get_by_user_id(user.id)
            if candidate and session.candidate_id == candidate.id:
                return

        raise ForbiddenException(message="You do not have permission to access this interview session")

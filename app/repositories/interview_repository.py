from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewSession, InterviewStatus, InterviewType


class IInterviewRepository(ABC):
    """Abstract interface repository for InterviewSession operations."""

    @abstractmethod
    async def create(self, session: InterviewSession) -> InterviewSession: ...

    @abstractmethod
    async def get_by_id(self, session_id: uuid.UUID) -> Optional[InterviewSession]: ...

    @abstractmethod
    async def update(self, session: InterviewSession) -> InterviewSession: ...

    @abstractmethod
    async def list_filtered(
        self,
        status: Optional[InterviewStatus] = None,
        candidate_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        interview_type: Optional[InterviewType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[InterviewSession], int]: ...


class SQLAlchemyInterviewRepository(IInterviewRepository):
    """Concrete SQLAlchemy 2.0 repository for InterviewSession entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, interview_session: InterviewSession) -> InterviewSession:
        self._session.add(interview_session)
        await self._session.flush()
        await self._session.refresh(interview_session)
        return interview_session

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[InterviewSession]:
        stmt = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.deleted_at.is_(None),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, interview_session: InterviewSession) -> InterviewSession:
        await self._session.flush()
        await self._session.refresh(interview_session)
        return interview_session

    async def list_filtered(
        self,
        status: Optional[InterviewStatus] = None,
        candidate_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        interview_type: Optional[InterviewType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[InterviewSession], int]:
        query = select(InterviewSession).where(InterviewSession.deleted_at.is_(None))

        if status:
            query = query.where(InterviewSession.status == status)
        if candidate_id:
            query = query.where(InterviewSession.candidate_id == candidate_id)
        if recruiter_id:
            query = query.where(InterviewSession.recruiter_id == recruiter_id)
        if interview_type:
            query = query.where(InterviewSession.interview_type == interview_type)
        if start_date:
            query = query.where(InterviewSession.scheduled_at >= start_date)
        if end_date:
            query = query.where(InterviewSession.scheduled_at <= end_date)

        # Count matching records
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await self._session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Order by created_at DESC with pagination
        query = query.order_by(InterviewSession.created_at.desc()).offset(offset).limit(limit)
        results = await self._session.execute(query)
        sessions = list(results.scalars().all())

        return sessions, total

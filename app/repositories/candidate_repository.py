from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate


class ICandidateRepository(ABC):
    """Abstract interface repository for Candidate persistence operations."""

    @abstractmethod
    async def create(self, candidate: Candidate) -> Candidate: ...

    @abstractmethod
    async def get_by_id(self, candidate_id: uuid.UUID) -> Optional[Candidate]: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Candidate]: ...

    @abstractmethod
    async def update(self, candidate: Candidate) -> Candidate: ...

    @abstractmethod
    async def search(
        self,
        skill: Optional[str] = None,
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Candidate], int]: ...


class SQLAlchemyCandidateRepository(ICandidateRepository):
    """Concrete SQLAlchemy 2.0 repository for Candidate entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, candidate: Candidate) -> Candidate:
        self._session.add(candidate)
        await self._session.flush()
        await self._session.refresh(candidate)
        return candidate

    async def get_by_id(self, candidate_id: uuid.UUID) -> Optional[Candidate]:
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Candidate]:
        stmt = select(Candidate).where(
            Candidate.user_id == user_id,
            Candidate.deleted_at.is_(None),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, candidate: Candidate) -> Candidate:
        await self._session.flush()
        await self._session.refresh(candidate)
        return candidate

    async def search(
        self,
        skill: Optional[str] = None,
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Candidate], int]:
        query = select(Candidate).where(Candidate.deleted_at.is_(None))

        if min_experience is not None:
            query = query.where(Candidate.experience_years >= min_experience)
        if max_experience is not None:
            query = query.where(Candidate.experience_years <= max_experience)
        if skill:
            # Filter JSONB skills array matching case-insensitive tag or contains
            query = query.where(
                Candidate.skills.contains([skill]) | Candidate.skills.cast(String).ilike(f"%{skill}%")
            )

        # Count total matching records
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await self._session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Paginated fetch ordered by created_at DESC
        query = query.order_by(Candidate.created_at.desc()).offset(offset).limit(limit)
        results = await self._session.execute(query)
        candidates = list(results.scalars().all())

        return candidates, total

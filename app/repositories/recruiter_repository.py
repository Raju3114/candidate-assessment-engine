from abc import ABC, abstractmethod
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recruiter import Recruiter


class IRecruiterRepository(ABC):
    """Abstract interface repository for Recruiter persistence operations."""

    @abstractmethod
    async def create(self, recruiter: Recruiter) -> Recruiter: ...

    @abstractmethod
    async def get_by_id(self, recruiter_id: uuid.UUID) -> Optional[Recruiter]: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Recruiter]: ...

    @abstractmethod
    async def update(self, recruiter: Recruiter) -> Recruiter: ...


class SQLAlchemyRecruiterRepository(IRecruiterRepository):
    """Concrete SQLAlchemy 2.0 repository for Recruiter entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, recruiter: Recruiter) -> Recruiter:
        self._session.add(recruiter)
        await self._session.flush()
        await self._session.refresh(recruiter)
        return recruiter

    async def get_by_id(self, recruiter_id: uuid.UUID) -> Optional[Recruiter]:
        stmt = select(Recruiter).where(
            Recruiter.id == recruiter_id,
            Recruiter.deleted_at.is_(None),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Recruiter]:
        stmt = select(Recruiter).where(
            Recruiter.user_id == user_id,
            Recruiter.deleted_at.is_(None),
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, recruiter: Recruiter) -> Recruiter:
        await self._session.flush()
        await self._session.refresh(recruiter)
        return recruiter

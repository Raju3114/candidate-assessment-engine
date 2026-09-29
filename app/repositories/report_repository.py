from abc import ABC, abstractmethod
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


class IReportRepository(ABC):
    """Abstract interface repository for Report entities."""

    @abstractmethod
    async def create(self, report: Report) -> Report: ...

    @abstractmethod
    async def get_by_interview(self, interview_id: uuid.UUID) -> Optional[Report]: ...

    @abstractmethod
    async def get_by_id(self, report_id: uuid.UUID) -> Optional[Report]: ...

    @abstractmethod
    async def update(self, report: Report) -> Report: ...


class SQLAlchemyReportRepository(IReportRepository):
    """Concrete SQLAlchemy 2.0 repository for Report entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, report: Report) -> Report:
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report)
        return report

    async def get_by_interview(self, interview_id: uuid.UUID) -> Optional[Report]:
        stmt = select(Report).where(Report.interview_id == interview_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, report_id: uuid.UUID) -> Optional[Report]:
        stmt = select(Report).where(Report.id == report_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, report: Report) -> Report:
        await self._session.flush()
        await self._session.refresh(report)
        return report

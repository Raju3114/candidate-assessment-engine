from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer


class IAnswerRepository(ABC):
    """Abstract interface repository for Answer entities."""

    @abstractmethod
    async def create(self, answer: Answer) -> Answer: ...

    @abstractmethod
    async def get_by_question(self, question_id: uuid.UUID) -> Optional[Answer]: ...

    @abstractmethod
    async def get_by_candidate(self, candidate_id: uuid.UUID) -> List[Answer]: ...


class SQLAlchemyAnswerRepository(IAnswerRepository):
    """Concrete SQLAlchemy 2.0 repository for Answer entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, answer: Answer) -> Answer:
        self._session.add(answer)
        await self._session.flush()
        await self._session.refresh(answer)
        return answer

    async def get_by_question(self, question_id: uuid.UUID) -> Optional[Answer]:
        stmt = select(Answer).where(Answer.question_id == question_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_candidate(self, candidate_id: uuid.UUID) -> List[Answer]:
        stmt = (
            select(Answer)
            where(Answer.candidate_id == candidate_id)
            order_by(Answer.submitted_at.asc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question


class IQuestionRepository(ABC):
    """Abstract interface repository for Question entities."""

    @abstractmethod
    async def create_many(self, questions: List[Question]) -> List[Question]: ...

    @abstractmethod
    async def get_by_interview(self, interview_id: uuid.UUID) -> List[Question]: ...

    @abstractmethod
    async def get_by_id(self, question_id: uuid.UUID) -> Optional[Question]: ...


class SQLAlchemyQuestionRepository(IQuestionRepository):
    """Concrete SQLAlchemy 2.0 repository for Question entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_many(self, questions: List[Question]) -> List[Question]:
        self._session.add_all(questions)
        await self._session.flush()
        for q in questions:
            await self._session.refresh(q)
        return questions

    async def get_by_interview(self, interview_id: uuid.UUID) -> List[Question]:
        stmt = (
            select(Question)
            where(Question.interview_id == interview_id)
            order_by(Question.sequence_number.asc())
        )
        results = await self._session.execute(stmt)
        return list(results.scalars().all())

    async def get_by_id(self, question_id: uuid.UUID) -> Optional[Question]:
        stmt = select(Question).where(Question.id == question_id)
        results = await self._session.execute(stmt)
        return results.scalar_one_or_none()

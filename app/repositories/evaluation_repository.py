from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.evaluation import AIEvaluation
from app.models.question import Question


class IAIEvaluationRepository(ABC):
    """Abstract interface repository for AIEvaluation persistence operations."""

    @abstractmethod
    async def create(self, evaluation: AIEvaluation) -> AIEvaluation: ...

    @abstractmethod
    async def get_by_answer(self, answer_id: uuid.UUID) -> Optional[AIEvaluation]: ...

    @abstractmethod
    async def get_by_id(self, evaluation_id: uuid.UUID) -> Optional[AIEvaluation]: ...

    @abstractmethod
    async def update(self, evaluation: AIEvaluation) -> AIEvaluation: ...

    @abstractmethod
    async def list_by_interview(self, interview_id: uuid.UUID) -> List[AIEvaluation]: ...


class SQLAlchemyEvaluationRepository(IAIEvaluationRepository):
    """Concrete SQLAlchemy 2.0 repository for AIEvaluation entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, evaluation: AIEvaluation) -> AIEvaluation:
        self._session.add(evaluation)
        await self._session.flush()
        await self._session.refresh(evaluation)
        return evaluation

    async def get_by_answer(self, answer_id: uuid.UUID) -> Optional[AIEvaluation]:
        stmt = select(AIEvaluation).where(AIEvaluation.answer_id == answer_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, evaluation_id: uuid.UUID) -> Optional[AIEvaluation]:
        stmt = select(AIEvaluation).where(AIEvaluation.id == evaluation_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, evaluation: AIEvaluation) -> AIEvaluation:
        await self._session.flush()
        await self._session.refresh(evaluation)
        return evaluation

    async def list_by_interview(self, interview_id: uuid.UUID) -> List[AIEvaluation]:
        stmt = (
            select(AIEvaluation)
            join(Answer, AIEvaluation.answer_id == Answer.id)
            join(Question, Answer.question_id == Question.id)
            where(Question.interview_id == interview_id)
            order_by(Question.sequence_number.asc())
        )
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

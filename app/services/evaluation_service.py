import json
import logging
from typing import List, Optional
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini_client import GeminiClient
from app.core.exceptions import NotFoundException
from app.models.evaluation import AIEvaluation
from app.models.user import User
from app.repositories.answer_repository import SQLAlchemyAnswerRepository
from app.repositories.evaluation_repository import IAIEvaluationRepository, SQLAlchemyEvaluationRepository
from app.repositories.question_repository import SQLAlchemyQuestionRepository
from app.schemas.evaluation import AIEvaluationResponse
from app.websocket.events import WSEventType
from app.websocket.manager import manager
from app.websocket.schemas import WSMessageEnvelope

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service encapsulating AI evaluation orchestration, Redis caching, and WebSocket notification dispatching."""

    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db_session = db_session
        self.redis = redis_client
        self.eval_repo: IAIEvaluationRepository = SQLAlchemyEvaluationRepository(db_session)
        self.answer_repo = SQLAlchemyAnswerRepository(db_session)
        self.question_repo = SQLAlchemyQuestionRepository(db_session)
        self.gemini_client = GeminiClient()

    async def evaluate_answer(self, answer_id: uuid.UUID) -> AIEvaluationResponse:
        """Invokes Gemini API to evaluate candidate answer, stores result, caches, and broadcasts WS event."""
        answer = await self.answer_repo.get_by_question(answer_id)
        if not answer:
            # Fallback direct lookup by ID
            stmt = await self.db_session.execute(
                select(Answer).where(Answer.id == answer_id)
            )
            answer = stmt.scalar_one_or_none()

        if not answer:
            raise NotFoundException(message=f"Answer record '{answer_id}' not found")

        question = await self.question_repo.get_by_id(answer.question_id)
        if not question:
            raise NotFoundException(message=f"Question record '{answer.question_id}' not found")

        # 1. Gemini Evaluation Prompt Execution
        result = await self.gemini_client.evaluate_answer(
            question_text=question.question_text,
            category=question.category,
            expected_topics=question.expected_topics,
            candidate_answer=answer.answer_text,
        )

        # 2. Check existing evaluation or create new
        existing_eval = await self.eval_repo.get_by_answer(answer.id)
        if existing_eval:
            existing_eval.technical_score = result.technical_score
            existing_eval.communication_score = result.communication_score
            existing_eval.relevance_score = result.relevance_score
            existing_eval.overall_score = result.overall_score
            existing_eval.strengths = result.strengths
            existing_eval.weaknesses = result.weaknesses
            existing_eval.improvement_suggestions = result.improvement_suggestions
            existing_eval.feedback_text = result.feedback_text
            existing_eval.status = "COMPLETED"
            eval_entity = await self.eval_repo.update(existing_eval)
        else:
            new_eval = AIEvaluation(
                answer_id=answer.id,
                technical_score=result.technical_score,
                communication_score=result.communication_score,
                relevance_score=result.relevance_score,
                overall_score=result.overall_score,
                strengths=result.strengths,
                weaknesses=result.weaknesses,
                improvement_suggestions=result.improvement_suggestions,
                feedback_text=result.feedback_text,
                status="COMPLETED",
                ai_model="gemini-1.5-pro",
                tokens_used=150,
            )
            eval_entity = await self.eval_repo.create(new_eval)

        await self.db_session.commit()
        response_dto = AIEvaluationResponse.model_validate(eval_entity)

        # 3. Write Redis Cache (TTL 1 hour)
        cache_key = f"evaluation:{str(answer.id)}"
        await self.redis.setex(cache_key, 3600, json.dumps(response_dto.model_dump(mode="json")))

        # 4. Broadcast EVALUATION_COMPLETED to WebSocket Room
        event = WSMessageEnvelope(
            event=WSEventType("EVALUATION_COMPLETED"),
            payload={
                "answer_id": str(answer.id),
                "overall_score": response_dto.overall_score,
                "feedback_text": response_dto.feedback_text,
                "status": "COMPLETED",
            },
        )
        await manager.broadcast_to_room(question.interview_id, event, redis_client=self.redis)

        return response_dto

    async def get_answer_evaluation(self, answer_id: uuid.UUID) -> AIEvaluationResponse:
        """Fetches AI evaluation with Redis cache-aside support."""
        cache_key = f"evaluation:{str(answer_id)}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(f"Redis Cache HIT for evaluation: {cache_key}")
            return AIEvaluationResponse.model_validate(json.loads(cached_data))

        logger.info(f"Redis Cache MISS for evaluation: {cache_key}")
        eval_entity = await self.eval_repo.get_by_answer(answer_id)
        if not eval_entity:
            raise NotFoundException(message=f"AI Evaluation for answer '{answer_id}' not found")

        response_dto = AIEvaluationResponse.model_validate(eval_entity)
        await self.redis.setex(cache_key, 3600, json.dumps(response_dto.model_dump(mode="json")))
        return response_dto

    async def list_interview_evaluations(self, interview_id: uuid.UUID) -> List[AIEvaluationResponse]:
        """Lists all completed AI evaluations for an interview session."""
        evals = await self.eval_repo.list_by_interview(interview_id)
        return [AIEvaluationResponse.model_validate(e) for e in evals]

import json
import logging
from typing import List, Optional
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini_client import GeminiClient
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.question import Question
from app.models.user import User, UserRole
from app.repositories.candidate_repository import SQLAlchemyCandidateRepository
from app.repositories.interview_repository import SQLAlchemyInterviewRepository
from app.repositories.question_repository import IQuestionRepository, SQLAlchemyQuestionRepository
from app.repositories.recruiter_repository import SQLAlchemyRecruiterRepository
from app.schemas.question import QuestionResponse

logger = logging.getLogger(__name__)


class QuestionGenerationService:
    """Service encapsulating AI-powered question generation, caching, and retrieval."""

    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db_session = db_session
        self.redis = redis_client
        self.question_repo: IQuestionRepository = SQLAlchemyQuestionRepository(db_session)
        self.interview_repo = SQLAlchemyInterviewRepository(db_session)
        self.candidate_repo = SQLAlchemyCandidateRepository(db_session)
        self.recruiter_repo = SQLAlchemyRecruiterRepository(db_session)
        self.gemini_client = GeminiClient()

    async def generate_questions_for_interview(
        self,
        user: User,
        interview_id: uuid.UUID,
        num_questions: int = 5,
        categories: Optional[List[str]] = None,
    ) -> List[QuestionResponse]:
        """Generates AI questions via Gemini API, saves to DB, and updates Redis cache."""
        if user.role != UserRole.RECRUITER and user.role != UserRole.ADMIN:
            raise ForbiddenException(message="Only recruiters can trigger AI question generation")

        session = await self.interview_repo.get_by_id(interview_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{interview_id}' not found")

        # Verify recruiter ownership
        if user.role == UserRole.RECRUITER:
            recruiter = await self.recruiter_repo.get_by_user_id(user.id)
            if not recruiter or session.recruiter_id != recruiter.id:
                raise ForbiddenException(message="You do not have permission to modify this interview session")

        candidate = await self.candidate_repo.get_by_id(session.candidate_id)
        candidate_skills = candidate.skills if candidate else []

        # Call Gemini AI Client
        raw_generated = await self.gemini_client.generate_questions(
            target_role=session.target_role,
            interview_type=session.interview_type.value,
            experience_level=session.experience_level,
            candidate_skills=candidate_skills,
            num_questions=num_questions,
            categories=categories,
        )

        # Check existing questions to calculate starting sequence_number
        existing_questions = await self.question_repo.get_by_interview(interview_id)
        start_seq = len(existing_questions) + 1

        question_entities = [
            Question(
                interview_id=interview_id,
                sequence_number=start_seq + idx,
                question_text=q.question_text,
                category=q.category,
                difficulty=q.difficulty,
                expected_topics=q.expected_topics,
                generated_by="AI",
            )
            for idx, q in enumerate(raw_generated)
        ]

        saved_questions = await self.question_repo.create_many(question_entities)
        await self.db_session.commit()

        # Update Redis Cache (Cache-Aside)
        response_dtos = [QuestionResponse.model_validate(q) for q in saved_questions]
        await self._cache_questions(interview_id, response_dtos)

        return response_dtos

    async def get_questions_by_interview(self, user: User, interview_id: uuid.UUID) -> List[QuestionResponse]:
        """Retrieves questions for an interview with Redis cache fallback."""
        session = await self.interview_repo.get_by_id(interview_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{interview_id}' not found")

        # Check Redis cache hit
        cache_key = f"questions:{str(interview_id)}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(f"Redis Cache HIT for interview questions: {cache_key}")
            raw_list = json.loads(cached_data)
            return [QuestionResponse.model_validate(item) for item in raw_list]

        logger.info(f"Redis Cache MISS for interview questions: {cache_key}")
        questions = await self.question_repo.get_by_interview(interview_id)
        response_dtos = [QuestionResponse.model_validate(q) for q in questions]

        if response_dtos:
            await self._cache_questions(interview_id, response_dtos)

        return response_dtos

    async def get_question_by_id(self, user: User, question_id: uuid.UUID) -> QuestionResponse:
        """Fetches a single question by UUID."""
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise NotFoundException(message=f"Question '{question_id}' not found")
        return QuestionResponse.model_validate(question)

    async def _cache_questions(self, interview_id: uuid.UUID, dtos: List[QuestionResponse]) -> None:
        """Serializes question DTOs and saves to Redis with 1-hour TTL."""
        cache_key = f"questions:{str(interview_id)}"
        serialized = json.dumps([d.model_dump(mode="json") for d in dtos])
        await self.redis.setex(cache_key, 3600, serialized)

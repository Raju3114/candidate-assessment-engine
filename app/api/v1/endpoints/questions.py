from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse
from app.dependencies.auth import get_current_active_user, role_required
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.models.user import User, UserRole
from app.schemas.question import QuestionGenerateRequest, QuestionResponse
from app.services.question_service import QuestionGenerationService

router = APIRouter(tags=["AI Question Generation"])


@router.post(
    "/interviews/{interview_id}/generate-questions",
    response_model=ApiResponse[List[QuestionResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI Interview Questions",
    description="Invokes Gemini API to generate structured questions tailored to the candidate profile and interview role.",
)
async def generate_questions_for_interview(
    interview_id: uuid.UUID,
    payload: QuestionGenerateRequest = QuestionGenerateRequest(),
    user: User = Depends(role_required([UserRole.RECRUITER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[List[QuestionResponse]]:
    service = QuestionGenerationService(db, redis)
    questions = await service.generate_questions_for_interview(
        user=user,
        interview_id=interview_id,
        num_questions=payload.num_questions,
        categories=payload.categories,
    )
    return ApiResponse.ok(questions)


@router.get(
    "/interviews/{interview_id}/questions",
    response_model=ApiResponse[List[QuestionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Interview Questions",
    description="Fetches all questions generated for an interview session with Redis cache-aside support.",
)
async def get_questions_by_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[List[QuestionResponse]]:
    service = QuestionGenerationService(db, redis)
    questions = await service.get_questions_by_interview(user, interview_id)
    return ApiResponse.ok(questions)


@router.get(
    "/questions/{question_id}",
    response_model=ApiResponse[QuestionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Single Question by ID",
    description="Returns detailed question metadata by question UUID.",
)
async def get_question_by_id(
    question_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[QuestionResponse]:
    service = QuestionGenerationService(db, redis)
    question = await service.get_question_by_id(user, question_id)
    return ApiResponse.ok(question)

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
from app.schemas.evaluation import AIEvaluationResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(tags=["AI Evaluation Engine"])


@router.get(
    "/answers/{answer_id}/evaluation",
    response_model=ApiResponse[AIEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Answer AI Evaluation",
    description="Fetches AI evaluation scores and qualitative feedback for a candidate answer.",
)
async def get_answer_evaluation(
    answer_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[AIEvaluationResponse]:
    service = EvaluationService(db, redis)
    evaluation = await service.get_answer_evaluation(answer_id)
    return ApiResponse.ok(evaluation)


@router.post(
    "/answers/{answer_id}/evaluate",
    response_model=ApiResponse[AIEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger Answer AI Evaluation",
    description="Triggers AI Gemini API evaluation for a specific candidate answer.",
)
async def evaluate_answer(
    answer_id: uuid.UUID,
    user: User = Depends(role_required([UserRole.RECRUITER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[AIEvaluationResponse]:
    service = EvaluationService(db, redis)
    evaluation = await service.evaluate_answer(answer_id)
    return ApiResponse.ok(evaluation)


@router.get(
    "/interviews/{interview_id}/evaluations",
    response_model=ApiResponse[List[AIEvaluationResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Interview Session AI Evaluations",
    description="Fetches all AI evaluations generated for an interview session.",
)
async def list_interview_evaluations(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiResponse[List[AIEvaluationResponse]]:
    service = EvaluationService(db, redis)
    evaluations = await service.list_interview_evaluations(interview_id)
    return ApiResponse.ok(evaluations)

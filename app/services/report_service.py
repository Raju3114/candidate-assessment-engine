from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini_client import GeminiClient
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.interview import InterviewStatus
from app.models.report import HiringRecommendation, Report
from app.models.user import User, UserRole
from app.repositories.candidate_repository import SQLAlchemyCandidateRepository
from app.repositories.evaluation_repository import SQLAlchemyEvaluationRepository
from app.repositories.interview_repository import SQLAlchemyInterviewRepository
from app.repositories.question_repository import SQLAlchemyQuestionRepository
from app.repositories.recruiter_repository import SQLAlchemyRecruiterRepository
from app.repositories.report_repository import IReportRepository, SQLAlchemyReportRepository
from app.schemas.report import ReportResponse
from app.websocket.events import WSEventType
from app.websocket.manager import manager
from app.websocket.schemas import WSMessageEnvelope

logger = logging.getLogger(__name__)


def compute_hiring_recommendation(overall_score: float) -> HiringRecommendation:
    """Deterministic hiring decision threshold rules."""
    score = round(overall_score, 1)
    if score >= 8.5:
        return HiringRecommendation.STRONG_HIRE
    elif score >= 7.0:
        return HiringRecommendation.HIRE
    elif score >= 5.5:
        return HiringRecommendation.NEUTRAL
    elif score >= 4.0:
        return HiringRecommendation.NO_HIRE
    else:
        return HiringRecommendation.STRONG_NO_HIRE


class ReportService:
    """Service handling interview report aggregation, deterministic hiring analytics, and Redis caching."""

    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db_session = db_session
        self.redis = redis_client
        self.report_repo: IReportRepository = SQLAlchemyReportRepository(db_session)
        self.interview_repo = SQLAlchemyInterviewRepository(db_session)
        self.question_repo = SQLAlchemyQuestionRepository(db_session)
        self.eval_repo = SQLAlchemyEvaluationRepository(db_session)
        self.recruiter_repo = SQLAlchemyRecruiterRepository(db_session)
        self.candidate_repo = SQLAlchemyCandidateRepository(db_session)
        self.gemini_client = GeminiClient()

    async def generate_report(self, user: User, interview_id: uuid.UUID) -> ReportResponse:
        """Aggregates evaluations, calculates skill analytics, calls Gemini, and saves report."""
        session = await self.interview_repo.get_by_id(interview_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{interview_id}' not found")

        # Permissions: Recruiter or Admin
        if user.role == UserRole.RECRUITER:
            recruiter = await self.recruiter_repo.get_by_user_id(user.id)
            if not recruiter or session.recruiter_id != recruiter.id:
                raise ForbiddenException(message="You do not have permission to generate a report for this interview")

        evaluations = await self.eval_repo.list_by_interview(interview_id)
        if not evaluations:
            raise BadRequestException(message="Cannot generate report: No answer evaluations found for this interview session")

        questions = await self.question_repo.get_by_interview(interview_id)
        q_map = {q.id: q for q in questions}

        # 1. Analytics Calculations
        avg_tech = round(sum(e.technical_score for e in evaluations) / len(evaluations), 1)
        avg_comm = round(sum(e.communication_score for e in evaluations) / len(evaluations), 1)
        avg_rel = round(sum(e.relevance_score for e in evaluations) / len(evaluations), 1)
        avg_overall = round(sum(e.overall_score for e in evaluations) / len(evaluations), 1)

        # 2. Skill Category Breakdown
        category_scores: Dict[str, List[float]] = {}
        evals_summary = []

        for e in evaluations:
            # Match answer back to question category
            ans = e.answer if hasattr(e, "answer") else None
            cat = "General"
            if ans and ans.question_id in q_map:
                cat = q_map[ans.question_id].category

            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(float(e.overall_score))

            evals_summary.append({
                "category": cat,
                "overall_score": float(e.overall_score),
                "feedback_text": e.feedback_text,
            })

        skill_breakdown = {
            cat: round(sum(scores) / len(scores), 1)
            for cat, scores in category_scores.items()
        }

        # 3. Deterministic Hiring Recommendation
        recommendation = compute_hiring_recommendation(avg_overall)

        # 4. Call Gemini for Executive Summary and Qualitative Synthesis
        gemini_report = await self.gemini_client.generate_final_report(
            target_role=session.target_role,
            experience_level=session.experience_level,
            overall_score=avg_overall,
            skill_breakdown=skill_breakdown,
            evaluations_summary=evals_summary,
        )

        # 5. Create or Update Report in PostgreSQL
        existing_report = await self.report_repo.get_by_interview(interview_id)
        if existing_report:
            existing_report.overall_score = avg_overall
            existing_report.technical_score = avg_tech
            existing_report.communication_score = avg_comm
            existing_report.relevance_score = avg_rel
            existing_report.strengths = gemini_report.strengths
            existing_report.weaknesses = gemini_report.weaknesses
            existing_report.skill_breakdown = skill_breakdown
            existing_report.recommendation = recommendation
            existing_report.executive_summary = gemini_report.executive_summary
            existing_report.generated_at = datetime.now(timezone.utc)
            report_entity = await self.report_repo.update(existing_report)
        else:
            new_report = Report(
                interview_id=interview_id,
                overall_score=avg_overall,
                technical_score=avg_tech,
                communication_score=avg_comm,
                relevance_score=avg_rel,
                strengths=gemini_report.strengths,
                weaknesses=gemini_report.weaknesses,
                skill_breakdown=skill_breakdown,
                recommendation=recommendation,
                executive_summary=gemini_report.executive_summary,
                generated_by="AI",
            )
            report_entity = await self.report_repo.create(new_report)

        # Update Interview Session status to COMPLETED
        session.status = InterviewStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        await self.interview_repo.update(session)

        await self.db_session.commit()
        response_dto = ReportResponse.model_validate(report_entity)

        # 6. Redis Cache (TTL 6 hours / 21600 seconds)
        cache_key = f"report:{str(interview_id)}"
        await self.redis.setex(cache_key, 21600, json.dumps(response_dto.model_dump(mode="json")))

        # 7. Broadcast REPORT_GENERATED WebSocket Event
        event = WSMessageEnvelope(
            event=WSEventType("REPORT_GENERATED"),
            payload={
                "interview_id": str(interview_id),
                "overall_score": response_dto.overall_score,
                "recommendation": response_dto.recommendation.value,
            },
        )
        await manager.broadcast_to_room(interview_id, event, redis_client=self.redis)

        return response_dto

    async def get_report_by_interview(self, user: User, interview_id: uuid.UUID) -> ReportResponse:
        """Retrieves interview report with Redis cache-aside support."""
        session = await self.interview_repo.get_by_id(interview_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{interview_id}' not found")

        # Permissions check
        if user.role == UserRole.CANDIDATE:
            candidate = await self.candidate_repo.get_by_user_id(user.id)
            if not candidate or session.candidate_id != candidate.id:
                raise ForbiddenException(message="You do not have access to this report")
        elif user.role == UserRole.RECRUITER:
            recruiter = await self.recruiter_repo.get_by_user_id(user.id)
            if not recruiter or session.recruiter_id != recruiter.id:
                raise ForbiddenException(message="You do not have access to this report")

        # Redis Cache Hit Check
        cache_key = f"report:{str(interview_id)}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(f"Redis Cache HIT for report: {cache_key}")
            return ReportResponse.model_validate(json.loads(cached_data))

        logger.info(f"Redis Cache MISS for report: {cache_key}")
        report_entity = await self.report_repo.get_by_interview(interview_id)
        if not report_entity:
            raise NotFoundException(message=f"Final report for interview '{interview_id}' not found")

        response_dto = ReportResponse.model_validate(report_entity)
        await self.redis.setex(cache_key, 21600, json.dumps(response_dto.model_dump(mode="json")))
        return response_dto

    async def get_report_by_id(self, user: User, report_id: uuid.UUID) -> ReportResponse:
        """Fetches a report by its UUID primary key."""
        report_entity = await self.report_repo.get_by_id(report_id)
        if not report_entity:
            raise NotFoundException(message=f"Report '{report_id}' not found")
        return ReportResponse.model_validate(report_entity)

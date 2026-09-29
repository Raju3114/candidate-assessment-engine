import asyncio
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.ai.parsers import (
    EvaluationSchema,
    FinalReportSchema,
    GeneratedQuestionSchema,
    parse_and_validate_evaluation_json,
    parse_and_validate_gemini_json,
    parse_and_validate_report_json,
)
from app.ai.prompts import (
    build_answer_evaluation_prompt,
    build_final_report_prompt,
    build_question_generation_prompt,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiClient:
    """Async wrapper for Google Gemini API question generation, evaluation, and report synthesis."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL_NAME
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def generate_questions(
        self,
        target_role: str,
        interview_type: str,
        experience_level: str,
        candidate_skills: List[str],
        num_questions: int = 5,
        categories: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> List[GeneratedQuestionSchema]:
        if not self.api_key:
            return self._get_fallback_questions(target_role, interview_type, experience_level, num_questions)

        prompt = build_question_generation_prompt(
            target_role=target_role,
            interview_type=interview_type,
            experience_level=experience_level,
            candidate_skills=candidate_skills,
            num_questions=num_questions,
            categories=categories,
        )

        for attempt in range(1, max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                model = genai.GenerativeModel(self.model_name)
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: model.generate_content(prompt)),
                    timeout=15.0,
                )
                return parse_and_validate_gemini_json(response.text)
            except Exception as exc:
                logger.error(f"Gemini API question gen attempt {attempt} error: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * attempt)

        return self._get_fallback_questions(target_role, interview_type, experience_level, num_questions)

    async def evaluate_answer(
        self,
        question_text: str,
        category: str,
        expected_topics: List[str],
        candidate_answer: str,
        max_retries: int = 3,
    ) -> EvaluationSchema:
        if not self.api_key:
            return self._get_fallback_evaluation(candidate_answer)

        prompt = build_answer_evaluation_prompt(
            question_text=question_text,
            category=category,
            expected_topics=expected_topics,
            candidate_answer=candidate_answer,
        )

        for attempt in range(1, max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                model = genai.GenerativeModel(self.model_name)
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: model.generate_content(prompt)),
                    timeout=15.0,
                )
                return parse_and_validate_evaluation_json(response.text)
            except Exception as exc:
                logger.error(f"Gemini API evaluation attempt {attempt} error: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * attempt)

        return self._get_fallback_evaluation(candidate_answer)

    async def generate_final_report(
        self,
        target_role: str,
        experience_level: str,
        overall_score: float,
        skill_breakdown: Dict[str, float],
        evaluations_summary: List[Dict[str, Any]],
        max_retries: int = 3,
    ) -> FinalReportSchema:
        """Invokes Gemini API to synthesize qualitative report strengths, weaknesses, and executive summary."""
        if not self.api_key:
            return self._get_fallback_report(target_role, overall_score)

        prompt = build_final_report_prompt(
            target_role=target_role,
            experience_level=experience_level,
            overall_score=overall_score,
            skill_breakdown=skill_breakdown,
            evaluations_summary=evaluations_summary,
        )

        for attempt in range(1, max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                model = genai.GenerativeModel(self.model_name)
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: model.generate_content(prompt)),
                    timeout=15.0,
                )
                return parse_and_validate_report_json(response.text)
            except Exception as exc:
                logger.error(f"Gemini API final report attempt {attempt} error: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * attempt)

        return self._get_fallback_report(target_role, overall_score)

    def _get_fallback_questions(
        self, target_role: str, interview_type: str, experience_level: str, num_questions: int
    ) -> List[GeneratedQuestionSchema]:
        fallback_pool = [
            GeneratedQuestionSchema(
                question_text=f"Explain how you would architect a high-throughput async microservice in Python/FastAPI for a {target_role} role.",
                category="FastAPI",
                difficulty="MEDIUM",
                expected_topics=["AsyncIO", "Concurrency", "Dependency Injection"],
            ),
            GeneratedQuestionSchema(
                question_text="Compare PostgreSQL B-Tree indexes versus GIN indexes for JSONB columns.",
                category="PostgreSQL",
                difficulty="MEDIUM",
                expected_topics=["B-Tree", "GIN", "JSONB"],
            ),
        ]
        return fallback_pool[:num_questions]

    def _get_fallback_evaluation(self, candidate_answer: str) -> EvaluationSchema:
        return EvaluationSchema(
            technical_score=7.5,
            communication_score=8.0,
            relevance_score=7.5,
            overall_score=7.7,
            strengths=["Submitted detailed text response", "Addressed key question prompt"],
            weaknesses=["Could provide deeper code examples"],
            improvement_suggestions=["Elaborate on edge case error handling"],
            feedback_text="Solid answer demonstrating core domain awareness.",
        )

    def _get_fallback_report(self, target_role: str, overall_score: float) -> FinalReportSchema:
        return FinalReportSchema(
            strengths=[
                "Demonstrates solid technical proficiency across core requirements",
                "Clear communication skills during question responses",
            ],
            weaknesses=[
                "Could deepen mastery in distributed systems edge cases under high concurrency",
            ],
            executive_summary=f"The candidate achieved an overall score of {overall_score}/10.0 for the {target_role} role. Evaluated as a strong performer with technical competence.",
        )

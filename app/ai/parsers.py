import json
import logging
import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class GeneratedQuestionSchema(BaseModel):
    question_text: str = Field(..., min_length=5)
    category: str = Field(default="General")
    difficulty: str = Field(default="MEDIUM")
    expected_topics: List[str] = Field(default_factory=list)

    def sanitize(self) -> "GeneratedQuestionSchema":
        diff = self.difficulty.upper()
        if diff not in ["EASY", "MEDIUM", "HARD"]:
            diff = "MEDIUM"

        cat = self.category.strip()
        valid_cats = ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "System Design", "Behavioral"]
        matched_cat = next((vc for vc in valid_cats if vc.lower() == cat.lower()), cat)

        return GeneratedQuestionSchema(
            question_text=self.question_text.strip(),
            category=matched_cat,
            difficulty=diff,
            expected_topics=[t.strip() for t in self.expected_topics if t and isinstance(t, str)],
        )


class GeneratedQuestionBatchSchema(BaseModel):
    questions: List[GeneratedQuestionSchema]


class EvaluationSchema(BaseModel):
    technical_score: float = Field(default=5.0, ge=0.0, le=10.0)
    communication_score: float = Field(default=5.0, ge=0.0, le=10.0)
    relevance_score: float = Field(default=5.0, ge=0.0, le=10.0)
    overall_score: float = Field(default=5.0, ge=0.0, le=10.0)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    feedback_text: str = Field(default="Candidate response evaluated.")

    def sanitize(self) -> "EvaluationSchema":
        def clamp(val: float) -> float:
            return round(max(0.0, min(10.0, float(val))), 1)

        return EvaluationSchema(
            technical_score=clamp(self.technical_score),
            communication_score=clamp(self.communication_score),
            relevance_score=clamp(self.relevance_score),
            overall_score=clamp(self.overall_score),
            strengths=[s.strip() for s in self.strengths if s],
            weaknesses=[w.strip() for w in self.weaknesses if w],
            improvement_suggestions=[i.strip() for i in self.improvement_suggestions if i],
            feedback_text=self.feedback_text.strip(),
        )


class FinalReportSchema(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    executive_summary: str = Field(default="Interview evaluation report compiled.")

    def sanitize(self) -> "FinalReportSchema":
        return FinalReportSchema(
            strengths=[s.strip() for s in self.strengths if s],
            weaknesses=[w.strip() for w in self.weaknesses if w],
            executive_summary=self.executive_summary.strip(),
        )


def parse_and_validate_gemini_json(raw_text: str) -> List[GeneratedQuestionSchema]:
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response text received from Gemini API")
    clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    clean_text = re.sub(r"\s*```$", "", clean_text, flags=re.MULTILINE).strip()
    data = json.loads(clean_text)
    batch = GeneratedQuestionBatchSchema.model_validate(data)
    return [q.sanitize() for q in batch.questions]


def parse_and_validate_evaluation_json(raw_text: str) -> EvaluationSchema:
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty evaluation response text received from Gemini API")
    clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    clean_text = re.sub(r"\s*```$", "", clean_text, flags=re.MULTILINE).strip()
    data = json.loads(clean_text)
    eval_obj = EvaluationSchema.model_validate(data)
    return eval_obj.sanitize()


def parse_and_validate_report_json(raw_text: str) -> FinalReportSchema:
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty report response text received from Gemini API")
    clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    clean_text = re.sub(r"\s*```$", "", clean_text, flags=re.MULTILINE).strip()
    data = json.loads(clean_text)
    report_obj = FinalReportSchema.model_validate(data)
    return report_obj.sanitize()

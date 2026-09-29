from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class QuestionCreate(BaseSchema):
    interview_id: uuid.UUID
    sequence_number: int = Field(..., ge=1)
    question_text: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(default="MEDIUM")
    expected_topics: List[str] = Field(default_factory=list)
    generated_by: str = Field(default="AI")


class QuestionResponse(BaseSchema):
    id: uuid.UUID
    interview_id: uuid.UUID
    sequence_number: int
    question_text: str
    category: str
    difficulty: str
    expected_topics: List[str]
    generated_by: str
    created_at: datetime


class QuestionGenerateRequest(BaseSchema):
    num_questions: int = Field(default=5, ge=1, le=10, description="Number of questions to generate")
    categories: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific categories e.g. ['Python', 'System Design']",
    )

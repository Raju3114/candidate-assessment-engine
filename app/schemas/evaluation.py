from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import Field

from app.schemas.common import BaseSchema


class AIEvaluationResponse(BaseSchema):
    id: uuid.UUID
    answer_id: uuid.UUID
    technical_score: float
    communication_score: float
    relevance_score: float
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]
    feedback_text: str
    status: str
    ai_model: str
    tokens_used: int
    evaluated_at: datetime

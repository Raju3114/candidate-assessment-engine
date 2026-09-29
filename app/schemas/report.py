from datetime import datetime
from typing import Dict, List, Optional
import uuid

from pydantic import Field

from app.models.report import HiringRecommendation
from app.schemas.common import BaseSchema


class ReportResponse(BaseSchema):
    id: uuid.UUID
    interview_id: uuid.UUID
    overall_score: float
    technical_score: float
    communication_score: float
    relevance_score: float
    strengths: List[str]
    weaknesses: List[str]
    skill_breakdown: Dict[str, float]
    recommendation: HiringRecommendation
    executive_summary: str
    generated_by: str
    generated_at: datetime

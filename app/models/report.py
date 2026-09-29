from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class HiringRecommendation(str, Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    NEUTRAL = "NEUTRAL"
    NO_HIRE = "NO_HIRE"
    STRONG_NO_HIRE = "STRONG_NO_HIRE"


class Report(BaseModel):
    __tablename__ = "reports"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Parent interview session ID",
    )
    overall_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Composite overall session performance score (0.0 - 10.0)",
    )
    technical_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Aggregate technical correctness score (0.0 - 10.0)",
    )
    communication_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Aggregate communication clarity score (0.0 - 10.0)",
    )
    relevance_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Aggregate answer relevance score (0.0 - 10.0)",
    )
    strengths: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Aggregated candidate strengths across all questions",
    )
    weaknesses: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Aggregated candidate skill gaps across all questions",
    )
    skill_breakdown: Mapped[Dict[str, float]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Categorized score dictionary e.g. {'Python': 8.5, 'FastAPI': 7.8}",
    )
    recommendation: Mapped[HiringRecommendation] = mapped_column(
        SQLEnum(HiringRecommendation, name="hiring_recommendation_enum", native_enum=False),
        nullable=False,
        default=HiringRecommendation.NEUTRAL,
        index=True,
        comment="Deterministic hiring recommendation decision",
    )
    executive_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="High-level candidate synthesis and hiring rationale",
    )
    generated_by: Mapped[str] = mapped_column(
        String(32),
        default="AI",
        nullable=False,
        comment="Generator source tag ('AI' or 'RECRUITER')",
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Generation timestamp",
    )

    # 1:1 Relationship back to InterviewSession
    interview_session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="report")

    def __repr__(self) -> str:
        return f"<Report id={self.id} interview_id={self.interview_id} recommendation='{self.recommendation}'>"

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AIEvaluation(BaseModel):
    __tablename__ = "ai_evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Target candidate answer ID",
    )
    technical_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Score for technical correctness (0.0 - 10.0)",
    )
    communication_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Score for communication clarity (0.0 - 10.0)",
    )
    relevance_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Score for answer relevance to prompt (0.0 - 10.0)",
    )
    overall_score: Mapped[float] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=0.0,
        comment="Composite overall score (0.0 - 10.0)",
    )
    strengths: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Array of highlighted candidate strengths",
    )
    weaknesses: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Array of identified candidate knowledge gaps",
    )
    improvement_suggestions: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Actionable feedback points for improvement",
    )
    feedback_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Qualitative summary feedback statement",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
        comment="Evaluation process status ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
    )
    ai_model: Mapped[str] = mapped_column(
        String(64),
        default="gemini-1.5-pro",
        nullable=False,
        comment="Gemini API model tag",
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total API tokens consumed",
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Completion timestamp",
    )

    # 1:1 Relationship back to Answer
    answer: Mapped["Answer"] = relationship("Answer", back_populates="evaluation")

    def __repr__(self) -> str:
        return f"<AIEvaluation id={self.id} answer_id={self.answer_id} overall_score={self.overall_score}>"

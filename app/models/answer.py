from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Answer(BaseModel):
    __tablename__ = "answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target question ID",
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Submitting candidate ID",
    )
    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Candidate text response transcript",
    )
    submitted_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Submission timestamp",
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="answers")
    evaluation: Mapped[Optional["AIEvaluation"]] = relationship(
        "AIEvaluation",
        back_populates="answer",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Answer id={self.id} question_id={self.question_id} candidate_id={self.candidate_id}>"

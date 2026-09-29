from typing import List, Optional
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Question(BaseModel):
    __tablename__ = "questions"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent interview session ID",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Display sequence order (1-N)",
    )
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Technical or behavioral prompt text",
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Topic category e.g. Python, FastAPI, PostgreSQL, System Design",
    )
    difficulty: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="MEDIUM",
        comment="Difficulty level e.g. EASY, MEDIUM, HARD",
    )
    expected_topics: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Rubric expected criteria or key evaluation concepts",
    )
    generated_by: Mapped[str] = mapped_column(
        String(32),
        default="AI",
        nullable=False,
        comment="Generation source ('AI' or 'RECRUITER')",
    )

    # 1:N Relationship back to InterviewSession
    interview_session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="questions"
    )

    # 1:N Relationship to Answers
    answers: Mapped[List["Answer"]] = relationship(
        "Answer",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} seq={self.sequence_number} category='{self.category}'>"

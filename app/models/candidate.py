from typing import Any, List, Optional
import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Candidate(BaseModel):
    __tablename__ = "candidates"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Associated user account ID",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Candidate full legal name",
    )
    headline: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Professional headline (e.g., Senior Full Stack Engineer)",
    )
    experience_years: Mapped[float] = mapped_column(
        Numeric(4, 1),
        default=0.0,
        nullable=False,
        comment="Total years of professional experience",
    )
    resume_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="S3/GCS Object URL to uploaded resume PDF",
    )
    skills: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Array of technical skills (e.g. ['Python', 'FastAPI'])",
    )
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="LinkedIn profile URL",
    )
    github_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub profile URL",
    )

    # 1:1 Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")

    # 1:N Relationship to InterviewSessions
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    # 1:N Relationship to Answers
    answers: Mapped[List["Answer"]] = relationship(
        "Answer",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} user_id={self.user_id} full_name='{self.full_name}'>"

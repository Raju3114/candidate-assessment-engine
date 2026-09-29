from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, BaseModel


class InterviewType(str, Enum):
    TECHNICAL = "TECHNICAL"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    BEHAVIORAL = "BEHAVIORAL"


class InterviewStatus(str, Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InterviewSession(BaseModel, AuditMixin):
    __tablename__ = "interview_sessions"

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Associated Recruiter ID",
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Associated Candidate ID",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Interview session title",
    )
    target_role: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Target job position (e.g., Staff Backend Engineer)",
    )
    experience_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="MID",
        comment="Seniority level e.g. JUNIOR, MID, SENIOR, LEAD",
    )
    interview_type: Mapped[InterviewType] = mapped_column(
        SQLEnum(InterviewType, name="interview_type_enum", native_enum=False),
        nullable=False,
        default=InterviewType.TECHNICAL,
        index=True,
        comment="Interview category type",
    )
    status: Mapped[InterviewStatus] = mapped_column(
        SQLEnum(InterviewStatus, name="interview_status_enum", native_enum=False),
        nullable=False,
        default=InterviewStatus.DRAFT,
        index=True,
        comment="Lifecycle status flag",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
        comment="Allocated duration limit in minutes",
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Planned interview start timestamp",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual interview start timestamp",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual interview completion timestamp",
    )

    # Relationships
    recruiter: Mapped["Recruiter"] = relationship("Recruiter", back_populates="interview_sessions")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="interview_sessions")
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="interview_session",
        cascade="all, delete-orphan",
        order_by="Question.sequence_number",
    )
    report: Mapped[Optional["Report"]] = relationship(
        "Report",
        back_populates="interview_session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<InterviewSession id={self.id} title='{self.title}' status='{self.status}'>"

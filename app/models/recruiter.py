from typing import List, Optional
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Recruiter(BaseModel):
    __tablename__ = "recruiters"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Associated user account ID",
    )
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Employer or recruitment agency name",
    )
    designation: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Job title / designation (e.g. Lead Tech Recruiter)",
    )
    company_website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Corporate domain / website URL",
    )
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Department name (e.g. Engineering Hiring)",
    )

    # 1:1 Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="recruiter_profile")

    # 1:N Relationship to InterviewSessions
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="recruiter",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recruiter id={self.id} user_id={self.user_id} company='{self.company_name}'>"

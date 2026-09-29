from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import Field, field_validator

from app.models.interview import InterviewStatus, InterviewType
from app.schemas.common import BaseSchema


class InterviewCreate(BaseSchema):
    candidate_id: uuid.UUID = Field(..., description="Target candidate UUID")
    title: str = Field(..., min_length=1, max_length=255, description="Session title e.g. Technical System Design Round")
    target_role: str = Field(..., min_length=1, max_length=150, description="Target job title")
    experience_level: str = Field(default="MID", description="Seniority level e.g. JUNIOR, MID, SENIOR, LEAD")
    interview_type: InterviewType = Field(default=InterviewType.TECHNICAL, description="Interview topic category")
    duration_minutes: int = Field(default=60, ge=15, le=240, description="Duration limit in minutes")
    scheduled_at: Optional[datetime] = Field(default=None, description="Planned schedule timestamp")


class InterviewSchedule(BaseSchema):
    scheduled_at: datetime = Field(..., description="New scheduled start time in UTC")


class InterviewUpdate(BaseSchema):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    target_role: Optional[str] = Field(default=None, min_length=1, max_length=150)
    experience_level: Optional[str] = Field(default=None)
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=240)


class InterviewResponse(BaseSchema):
    id: uuid.UUID
    recruiter_id: uuid.UUID
    candidate_id: uuid.UUID
    title: str
    target_role: str
    experience_level: str
    interview_type: InterviewType
    status: InterviewStatus
    duration_minutes: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None

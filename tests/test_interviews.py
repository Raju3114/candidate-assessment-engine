from datetime import datetime, timedelta, timezone
import uuid

import pytest

from app.models.interview import InterviewStatus, InterviewType
from app.schemas.interview import InterviewCreate, InterviewSchedule


@pytest.mark.asyncio
async def test_interview_create_schema():
    candidate_id = uuid.uuid4()
    scheduled_time = datetime.now(timezone.utc) + timedelta(days=2)

    payload = InterviewCreate(
        candidate_id=candidate_id,
        title="Senior Python Backend Technical Interview",
        target_role="Staff Software Engineer",
        experience_level="SENIOR",
        interview_type=InterviewType.TECHNICAL,
        duration_minutes=60,
        scheduled_at=scheduled_time,
    )

    assert payload.candidate_id == candidate_id
    assert payload.interview_type == InterviewType.TECHNICAL
    assert payload.duration_minutes == 60


@pytest.mark.asyncio
async def test_interview_status_enum_values():
    assert InterviewStatus.DRAFT.value == "DRAFT"
    assert InterviewStatus.SCHEDULED.value == "SCHEDULED"
    assert InterviewStatus.IN_PROGRESS.value == "IN_PROGRESS"
    assert InterviewStatus.COMPLETED.value == "COMPLETED"
    assert InterviewStatus.CANCELLED.value == "CANCELLED"

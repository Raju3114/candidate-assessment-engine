from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar
import uuid

from pydantic import BaseModel, Field

from app.websocket.events import WSEventType

T = TypeVar("T")


class WSMessageEnvelope(BaseModel, Generic[T]):
    event: WSEventType = Field(..., description="WebSocket event type identifier")
    payload: Optional[T] = Field(default=None, description="Event data payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event dispatch timestamp",
    )


class AnswerSubmittedPayload(BaseModel):
    question_id: uuid.UUID
    answer_text: str


class QuestionDeliveredPayload(BaseModel):
    question_id: uuid.UUID
    sequence_number: int
    question_text: str
    category: str
    difficulty: str
    total_questions: int


class ParticipantEventPayload(BaseModel):
    user_id: uuid.UUID
    role: str
    room_id: uuid.UUID

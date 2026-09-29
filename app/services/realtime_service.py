import json
import logging
from typing import Any, Dict, Optional
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.answer import Answer
from app.models.interview import InterviewStatus
from app.models.user import User, UserRole
from app.repositories.answer_repository import SQLAlchemyAnswerRepository
from app.repositories.candidate_repository import SQLAlchemyCandidateRepository
from app.repositories.interview_repository import SQLAlchemyInterviewRepository
from app.repositories.question_repository import SQLAlchemyQuestionRepository
from app.repositories.recruiter_repository import SQLAlchemyRecruiterRepository
from app.websocket.connection import WebSocketConnection
from app.websocket.events import WSEventType
from app.websocket.manager import manager
from app.websocket.schemas import (
    AnswerSubmittedPayload,
    ParticipantEventPayload,
    QuestionDeliveredPayload,
    WSMessageEnvelope,
)

logger = logging.getLogger(__name__)


class InterviewRealtimeService:
    """Service handling real-time WebSocket interview execution, answer submission, and state tracking."""

    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db_session = db_session
        self.redis = redis_client
        self.interview_repo = SQLAlchemyInterviewRepository(db_session)
        self.question_repo = SQLAlchemyQuestionRepository(db_session)
        self.answer_repo = SQLAlchemyAnswerRepository(db_session)
        self.candidate_repo = SQLAlchemyCandidateRepository(db_session)
        self.recruiter_repo = SQLAlchemyRecruiterRepository(db_session)

    async def join_room(self, user: User, interview_id: uuid.UUID, connection: WebSocketConnection) -> Dict[str, Any]:
        """Registers user connection into room, restores room state from Redis, and broadcasts arrival."""
        session = await self.interview_repo.get_by_id(interview_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{interview_id}' not found")

        await self._verify_session_access(user, session)
        await manager.connect(connection)

        # Update Redis State `interview_state:{interview_id}`
        state_key = f"interview_state:{str(interview_id)}"
        current_state = await self._get_redis_state(state_key)

        if user.role == UserRole.CANDIDATE:
            current_state["candidate_connected"] = True
        elif user.role == UserRole.RECRUITER:
            current_state["recruiter_connected"] = True

        current_state["status"] = session.status.value
        await self._save_redis_state(state_key, current_state)

        # Broadcast PARTICIPANT_JOINED
        event = WSMessageEnvelope(
            event=WSEventType.PARTICIPANT_JOINED,
            payload=ParticipantEventPayload(
                user_id=user.id,
                role=user.role.value,
                room_id=interview_id,
            ),
        )
        await manager.broadcast_to_room(interview_id, event, redis_client=self.redis, exclude_connection=connection)

        return current_state

    async def send_next_question(
        self, user: User, interview_id: uuid.UUID, target_seq: Optional[int] = None
    ) -> QuestionDeliveredPayload:
        """Pushes current or next question to all room participants."""
        session = await self.interview_repo.get_by_id(interview_id)
        if not session:
            raise NotFoundException(message=f"Interview session '{interview_id}' not found")

        questions = await self.question_repo.get_by_interview(interview_id)
        if not questions:
            raise BadRequestException(message="No questions found for this interview session. Please generate questions first.")

        state_key = f"interview_state:{str(interview_id)}"
        current_state = await self._get_redis_state(state_key)

        seq_idx = target_seq or (current_state.get("current_question_index", 0) + 1)
        if seq_idx > len(questions):
            raise BadRequestException(message="All questions for this interview session have already been delivered")

        target_question = next((q for q in questions if q.sequence_number == seq_idx), questions[0])
        current_state["current_question_index"] = seq_idx
        await self._save_redis_state(state_key, current_state)

        payload = QuestionDeliveredPayload(
            question_id=target_question.id,
            sequence_number=target_question.sequence_number,
            question_text=target_question.question_text,
            category=target_question.category,
            difficulty=target_question.difficulty,
            total_questions=len(questions),
        )

        event = WSMessageEnvelope(
            event=WSEventType.QUESTION_DELIVERED,
            payload=payload,
        )
        await manager.broadcast_to_room(interview_id, event, redis_client=self.redis)

        return payload

    async def submit_answer(
        self, user: User, interview_id: uuid.UUID, question_id: uuid.UUID, answer_text: str
    ) -> Answer:
        """Persists live answer to PostgreSQL and notifies recruiter over socket."""
        candidate = await self.candidate_repo.get_by_user_id(user.id)
        if not candidate:
            raise ForbiddenException(message="Only registered candidates can submit answers")

        question = await self.question_repo.get_by_id(question_id)
        if not question or question.interview_id != interview_id:
            raise NotFoundException(message="Question not found in current interview room")

        # Save to PostgreSQL
        answer = Answer(
            question_id=question_id,
            candidate_id=candidate.id,
            answer_text=answer_text.strip(),
        )
        saved = await self.answer_repo.create(answer)
        await self.db_session.commit()

        # Notify Recruiter socket
        event = WSMessageEnvelope(
            event=WSEventType.ANSWER_RECEIVED,
            payload={
                "question_id": str(question_id),
                "answer_id": str(saved.id),
                "candidate_id": str(candidate.id),
                "answer_text": saved.answer_text,
                "submitted_at": saved.submitted_at.isoformat(),
            },
        )
        await manager.broadcast_to_room(interview_id, event, redis_client=self.redis)

        return saved

    async def leave_room(self, user: User, connection: WebSocketConnection) -> None:
        """Handles connection disconnect, updates Redis room state, and notifies room."""
        manager.disconnect(connection)
        interview_id = connection.room_id

        state_key = f"interview_state:{str(interview_id)}"
        current_state = await self._get_redis_state(state_key)

        if user.role == UserRole.CANDIDATE:
            current_state["candidate_connected"] = False
        elif user.role == UserRole.RECRUITER:
            current_state["recruiter_connected"] = False

        await self._save_redis_state(state_key, current_state)

        event = WSMessageEnvelope(
            event=WSEventType.PARTICIPANT_LEFT,
            payload=ParticipantEventPayload(
                user_id=user.id,
                role=user.role.value,
                room_id=interview_id,
            ),
        )
        await manager.broadcast_to_room(interview_id, event, redis_client=self.redis)

    async def _get_redis_state(self, key: str) -> Dict[str, Any]:
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return {
            "current_question_index": 0,
            "status": "SCHEDULED",
            "candidate_connected": False,
            "recruiter_connected": False,
        }

    async def _save_redis_state(self, key: str, state: Dict[str, Any]) -> None:
        # TTL 4 hours (14400 seconds)
        await self.redis.setex(key, 14400, json.dumps(state))

    async def _verify_session_access(self, user: User, session: Any) -> None:
        if user.role == UserRole.ADMIN:
            return
        if user.role == UserRole.RECRUITER:
            recruiter = await self.recruiter_repo.get_by_user_id(user.id)
            if recruiter and session.recruiter_id == recruiter.id:
                return
        elif user.role == UserRole.CANDIDATE:
            candidate = await self.candidate_repo.get_by_user_id(user.id)
            if candidate and session.candidate_id == candidate.id:
                return
        raise ForbiddenException(message="You do not have access to this interview room")

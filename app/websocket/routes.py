import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis

from app.core.exceptions import BaseAppException
from app.core.security import decode_token
from app.database.redis import get_redis_client
from app.database.session import AsyncSessionFactory
from app.repositories.user_repository import SQLAlchemyUserRepository
from app.services.realtime_service import InterviewRealtimeService
from app.websocket.connection import WebSocketConnection
from app.websocket.events import WSEventType
from app.websocket.manager import manager
from app.websocket.schemas import WSMessageEnvelope

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Real-Time WebSockets"])


@router.websocket("/ws/interviews/{interview_id}")
async def interview_websocket_endpoint(
    websocket: WebSocket,
    interview_id: uuid.UUID,
    token: str = Query(..., description="JWT Access Token"),
):
    """
    Stateful WebSocket endpoint powering live candidate interviews.
    Handshake URI: ws://localhost:8000/ws/interviews/{interview_id}?token=<jwt>
    """
    # 1. Authenticate Handshake JWT Token
    try:
        payload = decode_token(token, is_refresh=False)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = uuid.UUID(user_id_str)
    except Exception as exc:
        logger.error(f"WebSocket auth failed: {exc}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Database Session & User Lookup
    async with AsyncSessionFactory() as db_session:
        user_repo = SQLAlchemyUserRepository(db_session)
        user = await user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        redis = get_redis_client()
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user.id,
            role=user.role.value,
            room_id=interview_id,
        )

        realtime_svc = InterviewRealtimeService(db_session, redis)

        # 3. Join Room & Restore State
        try:
            current_state = await realtime_svc.join_room(user, interview_id, connection)
        except BaseAppException as app_exc:
            logger.error(f"Failed joining room '{interview_id}': {app_exc.message}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Send initial ACK & state restoration message to client
        ack_msg = WSMessageEnvelope(
            event=WSEventType.JOIN_ROOM,
            payload={"status": "connected", "state": current_state},
        )
        await connection.send_json(ack_msg.model_dump(mode="json"))

        # 4. Event Processing Loop
        try:
            while True:
                data_text = await websocket.receive_text()
                connection.touch()

                try:
                    raw_event = json.loads(data_text)
                    event_type = raw_event.get("event")
                    event_payload = raw_event.get("payload", {})
                except Exception:
                    err_msg = WSMessageEnvelope(
                        event=WSEventType.ERROR,
                        payload={"message": "Malformed JSON event message"},
                    )
                    await connection.send_json(err_msg.model_dump(mode="json"))
                    continue

                # Handle Client Event Types
                if event_type == WSEventType.HEARTBEAT:
                    pong = WSMessageEnvelope(event=WSEventType.PONG, payload={"last_seen": connection.last_seen.isoformat()})
                    await connection.send_json(pong.model_dump(mode="json"))

                elif event_type == WSEventType.ANSWER_SUBMITTED:
                    q_id_str = event_payload.get("question_id")
                    ans_text = event_payload.get("answer_text", "")
                    if q_id_str and ans_text:
                        await realtime_svc.submit_answer(
                            user=user,
                            interview_id=interview_id,
                            question_id=uuid.UUID(q_id_str),
                            answer_text=ans_text,
                        )
                        ack = WSMessageEnvelope(
                            event=WSEventType.ANSWER_RECEIVED,
                            payload={"status": "received", "question_id": q_id_str},
                        )
                        await connection.send_json(ack.model_dump(mode="json"))

                elif event_type == WSEventType.LEAVE_ROOM:
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user '{user.id}' in room '{interview_id}'")
        except Exception as exc:
            logger.error(f"Error in WebSocket event loop: {exc}")
        finally:
            await realtime_svc.leave_room(user, connection)

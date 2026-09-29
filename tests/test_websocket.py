import uuid

import pytest

from app.websocket.events import WSEventType
from app.websocket.manager import ConnectionManager
from app.websocket.schemas import WSMessageEnvelope


def test_websocket_event_types():
    assert WSEventType.JOIN_ROOM.value == "JOIN_ROOM"
    assert WSEventType.ANSWER_SUBMITTED.value == "ANSWER_SUBMITTED"
    assert WSEventType.QUESTION_DELIVERED.value == "QUESTION_DELIVERED"
    assert WSEventType.ANSWER_RECEIVED.value == "ANSWER_RECEIVED"


def test_ws_message_envelope():
    msg = WSMessageEnvelope(
        event=WSEventType.QUESTION_DELIVERED,
        payload={"question_text": "What is Python?"},
    )
    serialized = msg.model_dump(mode="json")
    assert serialized["event"] == "QUESTION_DELIVERED"
    assert serialized["payload"]["question_text"] == "What is Python?"


def test_connection_manager_empty_room():
    mgr = ConnectionManager()
    room_id = uuid.uuid4()
    users = mgr.get_active_users(room_id)
    assert users == []

from datetime import datetime, timezone
import uuid

from fastapi import WebSocket


class WebSocketConnection:
    """Wrapper class encapsulating an active FastAPI WebSocket instance with metadata."""

    def __init__(self, websocket: WebSocket, user_id: uuid.UUID, role: str, room_id: uuid.UUID):
        self.websocket = websocket
        self.user_id = user_id
        self.role = role
        self.room_id = room_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_seen = datetime.now(timezone.utc)

    def touch(self) -> None:
        """Updates last_seen timestamp on heartbeat ping/pong."""
        self.last_seen = datetime.now(timezone.utc)

    async def send_json(self, data: dict) -> None:
        """Sends JSON payload over socket connection."""
        await self.websocket.send_json(data)

import json
import logging
from typing import Dict, List, Optional, Set
import uuid

from fastapi import WebSocket
from redis.asyncio import Redis

from app.websocket.connection import WebSocketConnection
from app.websocket.events import WSEventType
from app.websocket.schemas import WSMessageEnvelope

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Room-based Connection Manager supporting stateful sockets and Redis Pub/Sub broadcast backplane.
    """

    def __init__(self):
        # Maps room_id -> set of active WebSocketConnections
        self.rooms: Dict[uuid.UUID, Set[WebSocketConnection]] = {}

    async def connect(self, connection: WebSocketConnection) -> None:
        """Accepts socket handshake and registers connection into room."""
        await connection.websocket.accept()
        room_id = connection.room_id

        if room_id not in self.rooms:
            self.rooms[room_id] = set()

        self.rooms[room_id].add(connection)
        logger.info(f"User '{connection.user_id}' ({connection.role}) connected to room '{room_id}'")

    def disconnect(self, connection: WebSocketConnection) -> None:
        """Removes connection from room and cleans up empty rooms."""
        room_id = connection.room_id
        if room_id in self.rooms:
            self.rooms[room_id].discard(connection)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        logger.info(f"User '{connection.user_id}' disconnected from room '{room_id}'")

    async def send_personal_message(self, connection: WebSocketConnection, message: WSMessageEnvelope) -> None:
        """Sends targeted message to specific WebSocket connection."""
        try:
            await connection.send_json(message.model_dump(mode="json"))
        except Exception as exc:
            logger.error(f"Failed to send personal socket message to '{connection.user_id}': {exc}")

    async def broadcast_to_room(
        self,
        room_id: uuid.UUID,
        message: WSMessageEnvelope,
        redis_client: Optional[Redis] = None,
        exclude_connection: Optional[WebSocketConnection] = None,
    ) -> None:
        """
        Broadcasts message to all connections in room.
        Optionally publishes to Redis Pub/Sub for multi-instance horizontal scaling.
        """
        payload_dict = message.model_dump(mode="json")

        # 1. In-memory local socket broadcast
        if room_id in self.rooms:
            dead_connections = set()
            for conn in list(self.rooms[room_id]):
                if exclude_connection and conn == exclude_connection:
                    continue
                try:
                    await conn.send_json(payload_dict)
                except Exception as exc:
                    logger.error(f"Failed socket delivery to '{conn.user_id}': {exc}")
                    dead_connections.add(conn)

            for dead_conn in dead_connections:
                self.disconnect(dead_conn)

        # 2. Redis Pub/Sub Broadcast Backplane (Horizontal Scalability)
        if redis_client:
            try:
                channel = f"ws_channel:room:{str(room_id)}"
                await redis_client.publish(channel, json.dumps(payload_dict))
            except Exception as exc:
                logger.error(f"Failed Redis Pub/Sub broadcast on channel '{channel}': {exc}")

    def get_active_users(self, room_id: uuid.UUID) -> List[Dict[str, str]]:
        """Returns list of active user IDs and roles in room."""
        if room_id not in self.rooms:
            return []
        return [
            {"user_id": str(conn.user_id), "role": conn.role}
            for conn in self.rooms[room_id]
        ]


# Global ConnectionManager instance
manager = ConnectionManager()

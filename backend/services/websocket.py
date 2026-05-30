"""
VitalGuard v2 — Enhanced WebSocket Manager
Bidirectional per-user WebSocket connections with typed message protocol.
"""

import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("vitalguard.websocket")


class ConnectionManager:
    """
    Manages per-user WebSocket connections.

    Message types (server → client):
      vitals   — real-time vital signs
      risk     — rule engine risk assessment
      decision — agent pipeline output
      action   — action execution result
      trend    — trend data for prediction panel
      trace    — agent explainability trace
      system   — system status messages
      error    — error messages

    Message types (client → server):
      set_mode     — change simulation mode
      set_profile  — change patient profile
      location_update — update patient location
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: {user_id} (total: {len(self.active_connections[user_id])})")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: {user_id}")

    async def send_typed_message(self, user_id: str, msg_type: str, data: dict):
        """Send a typed JSON message to all connections for a user."""
        message = json.dumps({"type": msg_type, "data": data})
        await self.send_personal_message(message, user_id)

    async def send_personal_message(self, message: str, user_id: str):
        """Send a raw text message to all connections for a user."""
        if user_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect(ws, user_id)

    async def send_json(self, user_id: str, data: dict):
        """Send a JSON object to all connections for a user."""
        await self.send_personal_message(json.dumps(data), user_id)

    async def broadcast(self, message: str):
        """Broadcast to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def broadcast_typed(self, msg_type: str, data: dict):
        """Broadcast a typed message to all connected users."""
        message = json.dumps({"type": msg_type, "data": data})
        await self.broadcast(message)

    def is_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    @property
    def connected_users(self) -> list:
        return list(self.active_connections.keys())


manager = ConnectionManager()

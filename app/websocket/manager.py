# manager.py
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps conversation_id to a set of connected WebSockets
        self.rooms: dict[int, set[WebSocket]] = {}
        # Maps user_id to a set of connected WebSockets (handles multiple devices)
        self.active_users: dict[int, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, conversation_id: int, user_id: int):
        await ws.accept()
        self.rooms.setdefault(conversation_id, set()).add(ws)
        self.active_users.setdefault(user_id, set()).add(ws)

    def disconnect(self, ws: WebSocket, conversation_id: int, user_id: int):
        self.rooms.get(conversation_id, set()).discard(ws)
        if user_id in self.active_users:
            self.active_users[user_id].discard(ws)
            if not self.active_users[user_id]:
                del self.active_users[user_id]

    async def broadcast(self, conversation_id: int, data: dict):
        for ws in self.rooms.get(conversation_id, set()):
            await ws.send_json(data)

    def is_user_online(self, user_id: int) -> bool:
        """Check if a specific user has any active WebSocket connections."""
        return user_id in self.active_users and len(self.active_users[user_id]) > 0

    async def send_personal_message(self, user_id: int, data: dict):
        """Send a message specifically to a user's active WebSockets."""
        if self.is_user_online(user_id):
            for ws in self.active_users[user_id]:
                await ws.send_json(data)

manager = ConnectionManager()
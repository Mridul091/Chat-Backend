from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.websocket.auth import ws_authenticate
from app.websocket.manager import manager
from app.core.database import AsyncSessionLocal
from app.models.message import Message
from app.repositories.message import MessageRepository

router = APIRouter()

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(ws: WebSocket, conversation_id: int):
    token = ws.query_params.get("token")
    user_id = await ws_authenticate(token) 
    if not user_id:
        await ws.close(code=1008)  # Policy Violation
        return
    
    await manager.connect(ws, conversation_id, user_id)
    try:
        while True:
            data = await ws.receive_json()
            async with AsyncSessionLocal() as db:
                msg = Message(
                    conversation_id = conversation_id,
                    sender_id = user_id,
                    content = data["content"]
                )

                saved = await MessageRepository.create_message(db, msg)

                await manager.broadcast(conversation_id, {
                    "type": "message",
                    "id": saved.id,
                    "sender_id": user_id,
                    "content": saved.content,
                    "created_at": str(saved.created_at)
                })
    except WebSocketDisconnect:
        manager.disconnect(ws, conversation_id, user_id)
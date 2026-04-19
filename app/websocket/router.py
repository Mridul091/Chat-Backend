from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.websocket.auth import ws_authenticate
from app.websocket.manager import manager
from app.core.database import AsyncSessionLocal
from app.models.message import Message
from app.repositories.message import MessageRepository
from app.repositories.conversation import ConversationRepository

router = APIRouter()


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(ws: WebSocket, conversation_id: int):
    await ws.accept()

    auth_msg = await ws.receive_json()
    token = auth_msg.get("token")

    user_id = await ws_authenticate(token)
    if not user_id:
        await ws.close(code=1008)  # Policy Violation
        return

    await manager.connect(ws, conversation_id, user_id)
    try:
        while True:
            data = await ws.receive_json()

            # 1. Enforce WebSocket Rate Limiting
            if not manager.check_rate_limit(user_id, max_messages=5, time_window=1.0):
                await ws.send_json(
                    {"type": "error", "message": "Rate limit exceeded. Please wait."}
                )
                continue  # Skip processing this message

            async with AsyncSessionLocal() as db:
                if not await ConversationRepository.is_member(
                    db, conversation_id, user_id
                ):
                    await ws.close(code=1008)
                    return
                content = data.get("content", "").strip()
                if not content or len(content) > 4000:
                    await ws.send_json(
                        {"type": "error", "message": "Invalid message content."}
                    )
                    continue

                msg = Message(
                    conversation_id=conversation_id, sender_id=user_id, content=content
                )

                saved = await MessageRepository.create_message(db, msg)

                await manager.broadcast(
                    conversation_id,
                    {
                        "type": "message",
                        "id": saved.id,
                        "sender_id": user_id,
                        "content": saved.content,
                        "created_at": str(saved.created_at),
                    },
                )
    except WebSocketDisconnect:
        manager.disconnect(ws, conversation_id, user_id)

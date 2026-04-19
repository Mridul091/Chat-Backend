from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from sqlalchemy import select
from datetime import datetime
from fastapi import HTTPException
class MessageRepository:

    async def create_message(db: AsyncSession, message: Message):
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_messages(db: AsyncSession, conversation_id: int, limit: int = 20, offset: int = 0):
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_messages_since(db: AsyncSession, conversation_id: int, since: str):
        # Convert string to datetime object to pass to PostgreSQL
        try:
            if since.endswith('Z'):
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            else:
                since_dt = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format")

        result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.created_at > since_dt
            ).order_by(Message.created_at.asc())
        )

        return result.scalars().all()

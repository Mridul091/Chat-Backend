from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from sqlalchemy import select


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

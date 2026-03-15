from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from sqlalchemy import select, update
from sqlalchemy.sql import func


class ConversationRepository:

    async def create_conversation(db: AsyncSession, conversation: Conversation):
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    async def get_conversation_by_id(db: AsyncSession, conversation_id: int):
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_user_conversations(db: AsyncSession, user_id: int):
        result = await db.execute(
            select(Conversation)
            .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
            .where(ConversationMember.user_id == user_id)
        )
        return result.scalars().all()

    async def add_member(db: AsyncSession, conversation_id: int, user_id: int):
        member = ConversationMember(conversation_id=conversation_id, user_id=user_id)
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member

    @staticmethod
    async def is_member(db: AsyncSession, conversation_id: int, user_id: int) -> bool:
        result = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def mark_conversation_read(db: AsyncSession, conversation_id: int, user_id: int):
        await db.execute(
            update(ConversationMember)
            .where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id
            )
            .values(last_read_at=func.now())
        )
        await db.commit()

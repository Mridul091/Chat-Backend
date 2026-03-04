from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.repositories.conversation import ConversationRepository
from app.schemas.conversation import ConversationCreate


async def create_conversation_with_members(
    db: AsyncSession,
    creator_id: int,
    data: ConversationCreate,
) -> Conversation:
    # 1. Create the conversation
    conversation = Conversation(
        type=data.type,
        title=data.title,
        created_by=creator_id,
    )
    saved = await ConversationRepository.create_conversation(db, conversation)

    # 2. Add creator as a member
    await ConversationRepository.add_member(db, saved.id, creator_id)

    # 3. Add all other members
    for user_id in data.member_ids:
        if user_id != creator_id:  # avoid duplicate if creator included themselves
            await ConversationRepository.add_member(db, saved.id, user_id)

    return saved

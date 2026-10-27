from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.repositories.conversation import ConversationRepository
from app.repositories.user import UserRepository
from app.schemas.conversation import ConversationCreate


async def create_conversation_with_members(
    db: AsyncSession,
    creator_id: int,
    data: ConversationCreate,
) -> Conversation:
    # 1. Validate the other members up front so nothing is written on failure
    other_ids = set(data.member_ids) - {creator_id}
    if other_ids:
        found = await UserRepository.get_users_by_ids(db, list(other_ids))
        missing = other_ids - {user.id for user in found}
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown user ids: {sorted(missing)}",
            )

    # 2. A DM is exactly two people, and there is only ever one per pair
    if data.type == "dm":
        if len(other_ids) != 1:
            raise HTTPException(
                status_code=400,
                detail="A direct message must have exactly one other member",
            )
        existing = await ConversationRepository.get_dm_between(
            db, creator_id, next(iter(other_ids))
        )
        if existing:
            return existing

    # 3. Create the conversation and all memberships in a single commit
    conversation = Conversation(
        type=data.type,
        title=data.title,
        created_by=creator_id,
        members=[
            ConversationMember(user_id=user_id) for user_id in {creator_id, *other_ids}
        ],
    )
    return await ConversationRepository.create_conversation(db, conversation)

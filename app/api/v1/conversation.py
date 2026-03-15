from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.models.message import Message
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.conversation import ConversationCreate, ConversationResponse, MemberAddRequest
from app.schemas.message import MessageCreate, MessageResponse
from app.services.conversation import create_conversation_with_members
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await create_conversation_with_members(db, current_user.id, data)
    return conversation


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ConversationRepository.get_user_conversations(db, current_user.id)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await ConversationRepository.get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not await ConversationRepository.is_member(db, conversation_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return conversation


@router.post("/{conversation_id}/members")
async def add_member(
    conversation_id: int,
    data: MemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await ConversationRepository.is_member(db, conversation_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    await ConversationRepository.add_member(db, conversation_id, data.user_id)
    return {"message": "Member added"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await ConversationRepository.is_member(db, conversation_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=data.content,
    )
    return await MessageRepository.create_message(db, message)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: int = 20,
    offset: int = 0,
    since: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await ConversationRepository.is_member(db, conversation_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if since:
        # Fetch only messages created after the provided timestamp
        return await MessageRepository.get_messages_since(db, conversation_id, since)
        
    return await MessageRepository.get_messages(db, conversation_id, limit, offset)

@router.post("/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await ConversationRepository.is_member(db, conversation_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    await ConversationRepository.mark_conversation_read(db, conversation_id, current_user.id)
    return {"message": "Conversation marked as read"}


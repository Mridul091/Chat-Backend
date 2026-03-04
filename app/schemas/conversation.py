from pydantic import BaseModel
from datetime import datetime

class ConversationCreate(BaseModel):
    title: str | None = None
    member_ids: list[int]
    type: str

class MemberAddRequest(BaseModel):
    user_id: int

class ConversationResponse(BaseModel):
    id: int
    title: str | None
    type: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


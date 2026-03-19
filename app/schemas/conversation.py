from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    member_ids: list[int] = Field(max_length=50)
    type: Literal["dm", "group"]

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


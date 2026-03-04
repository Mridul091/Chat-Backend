from pydantic import BaseModel
from datetime import datetime


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

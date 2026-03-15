from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, String
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship

class ConversationMember(Base):
    __tablename__ = "conversation_members"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_read_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User", back_populates="conversations")

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id"),
    )
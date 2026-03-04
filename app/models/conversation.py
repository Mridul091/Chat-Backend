from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
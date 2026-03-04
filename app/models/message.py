from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")
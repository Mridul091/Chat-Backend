from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    password_hash = Column(String, nullable=False)

    conversations = relationship(
        "ConversationMember",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    messages = relationship("Message", back_populates="sender")

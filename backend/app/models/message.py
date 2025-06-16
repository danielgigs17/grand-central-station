from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.db.base import Base


class MessageDirection(enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class MessageStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    platform_message_id = Column(String)
    
    direction = Column(Enum(MessageDirection), nullable=False)
    status = Column(Enum(MessageStatus), default=MessageStatus.PENDING)
    
    content = Column(Text)
    content_type = Column(String, default="text")  # text, image, video, tap, etc.
    
    # Metadata
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    ai_generated = Column(Boolean, default=False)
    ai_response_id = Column(UUID(as_uuid=True), ForeignKey("ai_responses.id"))
    
    # Timestamps from platform
    platform_timestamp = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    media = relationship("MessageMedia", back_populates="message", cascade="all, delete-orphan")
    ai_response = relationship("AIResponse", back_populates="messages")


class MessageMedia(Base):
    __tablename__ = "message_media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    media_type = Column(String, nullable=False)  # photo, video, audio
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    url = Column(String)  # Original URL if available
    media_metadata = Column(Text)  # JSON string for dimensions, duration, etc.
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    message = relationship("Message", back_populates="media")
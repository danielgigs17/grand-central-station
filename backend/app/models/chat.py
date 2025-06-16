from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class ChatCategory(Base):
    __tablename__ = "chat_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)  # hookup, work, personal
    color = Column(String)
    icon = Column(String)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    chats = relationship("Chat", back_populates="category")


class ChatGroup(Base):
    __tablename__ = "chat_groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    chats = relationship("Chat", secondary="chat_group_members", back_populates="groups")


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    platform_chat_id = Column(String)  # Platform-specific chat ID
    category_id = Column(UUID(as_uuid=True), ForeignKey("chat_categories.id"))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)
    unread_count = Column(Integer, default=0)
    
    # AI settings
    ai_enabled = Column(Boolean, default=False)
    ai_provider = Column(String)  # openai, anthropic
    ai_prompt = Column(Text)
    ai_temperature = Column(Integer, default=7)  # 0-10, maps to 0.0-1.0
    
    # Timestamps
    last_message_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    account = relationship("PlatformAccount", back_populates="chats")
    profile = relationship("Profile", back_populates="chats")
    category = relationship("ChatCategory", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    automation_rules = relationship("AutomationRule", back_populates="chat", cascade="all, delete-orphan")
    groups = relationship("ChatGroup", secondary="chat_group_members", back_populates="chats")
    hookup_history = relationship("HookupHistory", back_populates="chat", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="chat", cascade="all, delete-orphan")


# Association table for many-to-many relationship
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

chat_group_members = Table(
    "chat_group_members",
    Base.metadata,
    Column("chat_id", UUID(as_uuid=True), ForeignKey("chats.id"), primary_key=True),
    Column("group_id", UUID(as_uuid=True), ForeignKey("chat_groups.id"), primary_key=True),
)
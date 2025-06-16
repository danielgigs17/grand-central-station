from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class Platform(Base):
    __tablename__ = "platforms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)  # grindr, sniffies, alibaba
    display_name = Column(String, nullable=False)
    base_url = Column(String)
    api_base_url = Column(String)
    rate_limit_config = Column(JSON, default={})
    custom_headers = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    accounts = relationship("PlatformAccount", back_populates="platform")


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_id = Column(UUID(as_uuid=True), ForeignKey("platforms.id"), nullable=False)
    username = Column(String, nullable=False)
    password = Column(String)  # Encrypted
    session_data = Column(JSON, default={})  # Cookies, tokens, etc.
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime(timezone=True))
    last_error = Column(String)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    platform = relationship("Platform", back_populates="accounts")
    profiles = relationship("Profile", back_populates="account")
    chats = relationship("Chat", back_populates="account")
from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False)
    platform_user_id = Column(String, nullable=False)  # Platform-specific user ID
    username = Column(String)
    display_name = Column(String)
    
    # Common profile fields
    bio = Column(Text)
    age = Column(Integer)
    location = Column(String)
    distance = Column(Float)
    last_seen = Column(DateTime(timezone=True))
    
    # Platform-specific data stored as JSON
    platform_data = Column(JSON, default={})
    # Grindr: {position, race, weight, height, tribes, stats, looking_for, etc.}
    # Sniffies: {race, cruising_preference, etc.}
    # Alibaba: {company_name, business_type, etc.}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    account = relationship("PlatformAccount", back_populates="profiles")
    media = relationship("ProfileMedia", back_populates="profile", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="profile")


class ProfileMedia(Base):
    __tablename__ = "profile_media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    media_type = Column(String, nullable=False)  # photo, video, album
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    url = Column(String)  # Original URL if available
    media_metadata = Column(JSON, default={})  # dimensions, size, album_name, etc.
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    profile = relationship("Profile", back_populates="media")
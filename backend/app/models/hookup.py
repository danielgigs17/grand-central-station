from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class HookupHistory(Base):
    __tablename__ = "hookup_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    
    # Meeting details
    date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String)
    duration_minutes = Column(Integer)
    
    # Experience details
    rating = Column(Integer)  # 1-5
    notes = Column(Text)
    activities = Column(JSON, default=[])  # List of activities
    
    # Health/safety
    protection_used = Column(String)
    tested_after = Column(Boolean, default=False)
    test_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    chat = relationship("Chat", back_populates="hookup_history")
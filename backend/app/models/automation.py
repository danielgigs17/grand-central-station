from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"))
    
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Rule configuration
    is_active = Column(Boolean, default=True)
    rule_type = Column(String, nullable=False)  # keyword, pattern, time_based
    conditions = Column(JSON, default={})
    # For keyword: {keywords: ["hi", "hello"], match_type: "any"|"all"}
    # For pattern: {regex: ".*looking.*"}
    # For time_based: {start_hour: 9, end_hour: 17, days: ["mon", "tue"]}
    
    # Action configuration
    action_type = Column(String, nullable=False)  # ai_response, template_response, notify
    action_config = Column(JSON, default={})
    # For ai_response: {prompt_override: "...", temperature: 0.7}
    # For template: {template: "I'm not available right now"}
    
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    chat = relationship("Chat", back_populates="automation_rules")


class AIResponse(Base):
    __tablename__ = "ai_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request details
    provider = Column(String, nullable=False)  # openai, anthropic
    model = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    temperature = Column(Integer)
    
    # Response details
    response = Column(Text)
    usage = Column(JSON)  # tokens used, cost, etc.
    error = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    messages = relationship("Message", back_populates="ai_response")
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatCategoryBase(BaseModel):
    name: str
    color: Optional[str] = None
    icon: Optional[str] = None
    order: int = 0


class ChatCategoryCreate(ChatCategoryBase):
    pass


class ChatCategory(ChatCategoryBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatBase(BaseModel):
    category_id: Optional[UUID] = None
    ai_enabled: bool = False
    ai_provider: Optional[str] = None
    ai_prompt: Optional[str] = None
    ai_temperature: int = Field(7, ge=0, le=10)


class ChatCreate(ChatBase):
    account_id: UUID
    profile_id: UUID
    platform_chat_id: Optional[str] = None


class ChatUpdate(BaseModel):
    category_id: Optional[UUID] = None
    ai_enabled: Optional[bool] = None
    ai_provider: Optional[str] = None
    ai_prompt: Optional[str] = None
    ai_temperature: Optional[int] = Field(None, ge=0, le=10)
    is_starred: Optional[bool] = None
    is_muted: Optional[bool] = None
    is_archived: Optional[bool] = None


class Chat(ChatBase):
    id: UUID
    account_id: UUID
    profile_id: UUID
    platform_chat_id: Optional[str]
    is_active: bool
    is_archived: bool
    is_starred: bool
    is_muted: bool
    unread_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Relations
    category: Optional[ChatCategory] = None
    
    class Config:
        from_attributes = True


class ChatWithDetails(Chat):
    profile_username: str
    profile_display_name: Optional[str]
    platform_name: str
    last_message_content: Optional[str] = None
    last_message_time: Optional[datetime] = None
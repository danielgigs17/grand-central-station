from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.message import MessageDirection, MessageStatus


class MessageMediaBase(BaseModel):
    media_type: str
    url: Optional[str] = None
    metadata: Optional[dict] = None


class MessageMedia(MessageMediaBase):
    id: UUID
    file_path: str
    thumbnail_path: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    content: Optional[str] = None
    content_type: str = "text"


class MessageCreate(MessageBase):
    chat_id: UUID
    direction: MessageDirection
    platform_message_id: Optional[str] = None
    platform_timestamp: Optional[datetime] = None


class MessageUpdate(BaseModel):
    status: Optional[MessageStatus] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


class Message(MessageBase):
    id: UUID
    chat_id: UUID
    platform_message_id: Optional[str]
    direction: MessageDirection
    status: MessageStatus
    is_deleted: bool
    deleted_at: Optional[datetime]
    ai_generated: bool
    platform_timestamp: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime
    
    media: List[MessageMedia] = []
    
    class Config:
        from_attributes = True


class MessageSend(BaseModel):
    chat_id: UUID
    content: str
    media_urls: Optional[List[str]] = None
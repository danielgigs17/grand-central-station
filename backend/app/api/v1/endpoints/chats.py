from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.db.base import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.schemas.chat import ChatResponse

router = APIRouter()


@router.get("/", response_model=List[ChatResponse])
async def list_chats(
    limit: int = 100,
    offset: int = 0,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all chats with their latest message and profile info"""
    query = db.query(Chat)
    
    # Filter by category if provided
    if category:
        # For now, categorize based on platform
        if category == 'work':
            query = query.join(Chat.account).filter(
                Chat.account.has(platform_id='alibaba')
            )
        elif category == 'hookups':
            query = query.join(Chat.account).filter(
                Chat.account.has(platform_id='grindr')
            )
    
    # Get active chats first, then by last message time
    query = query.filter(Chat.is_active == True).order_by(
        Chat.last_message_at.desc().nullslast()
    )
    
    chats = query.offset(offset).limit(limit).all()
    
    # Get last message for each chat
    chat_responses = []
    for chat in chats:
        last_message = db.query(Message).filter(
            Message.chat_id == chat.id
        ).order_by(Message.created_at.desc()).first()
        
        # Extract contact name from platform_chat_id for now
        contact_name = chat.platform_chat_id.replace('chat_', '').replace('_', ' ').title()
        
        chat_data = {
            "id": str(chat.id),
            "account_id": str(chat.account_id),
            "profile_id": str(chat.profile_id) if chat.profile_id else None,
            "platform_chat_id": chat.platform_chat_id,
            "is_active": chat.is_active,
            "is_archived": chat.is_archived,
            "is_starred": chat.is_starred,
            "is_muted": chat.is_muted,
            "unread_count": chat.unread_count,
            "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
            "profile": {
                "id": str(chat.profile_id) if chat.profile_id else "unknown",
                "name": contact_name,
                "username": contact_name.lower().replace(' ', '_'),
                "avatar_url": None,
                "bio": None,
                "location": None,
                "is_active": True
            },
            "platform": {
                "id": "alibaba",
                "name": "alibaba",
                "display_name": "Alibaba",
                "icon_url": None,
                "is_active": True
            },
            "last_message": {
                "id": str(last_message.id),
                "content": last_message.content,
                "direction": last_message.direction.value,
                "created_at": last_message.created_at.isoformat(),
                "sender_name": contact_name if last_message.direction.value == 'INCOMING' else None
            } if last_message else None
        }
        chat_responses.append(chat_data)
    
    return chat_responses


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(chat_id: str, db: Session = Depends(get_db)):
    """Get a specific chat by ID"""
    chat = db.query(Chat).options(
        joinedload(Chat.profile),
        joinedload(Chat.account).joinedload('platform')
    ).filter(Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get last message
    last_message = db.query(Message).filter(
        Message.chat_id == chat.id
    ).order_by(Message.created_at.desc()).first()
    
    return {
        "id": str(chat.id),
        "account_id": str(chat.account_id),
        "profile_id": str(chat.profile_id) if chat.profile_id else None,
        "platform_chat_id": chat.platform_chat_id,
        "is_active": chat.is_active,
        "is_archived": chat.is_archived,
        "is_starred": chat.is_starred,
        "is_muted": chat.is_muted,
        "unread_count": chat.unread_count,
        "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat(),
        "profile": {
            "id": str(chat.profile.id),
            "name": chat.profile.name,
            "username": chat.profile.username,
            "avatar_url": chat.profile.avatar_url,
            "bio": chat.profile.bio,
            "location": chat.profile.location,
            "is_active": chat.profile.is_active
        } if chat.profile else None,
        "platform": {
            "id": str(chat.account.platform.id),
            "name": chat.account.platform.name,
            "display_name": chat.account.platform.display_name,
            "icon_url": chat.account.platform.icon_url,
            "is_active": chat.account.platform.is_active
        } if chat.account and chat.account.platform else None,
        "last_message": {
            "id": str(last_message.id),
            "content": last_message.content,
            "direction": last_message.direction.value,
            "created_at": last_message.created_at.isoformat(),
            "sender_name": getattr(last_message, 'sender_name', None)
        } if last_message else None
    }


@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get messages for a specific chat"""
    # Verify chat exists
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get messages ordered by creation time (newest first for pagination, but we'll reverse for display)
    messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
    
    # Reverse to show oldest first in the response
    messages.reverse()
    
    return [
        {
            "id": str(msg.id),
            "chat_id": str(msg.chat_id),
            "platform_message_id": msg.platform_message_id,
            "direction": msg.direction.value,
            "status": msg.status.value if msg.status else None,
            "content": msg.content,
            "content_type": msg.content_type,
            "is_deleted": msg.is_deleted,
            "ai_generated": msg.ai_generated,
            "platform_timestamp": msg.platform_timestamp.isoformat() if msg.platform_timestamp else None,
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "created_at": msg.created_at.isoformat(),
            "is_reply": msg.is_reply,
            "reply_to_content": msg.reply_to_content,
            "sender_name": getattr(msg, 'sender_name', None)
        }
        for msg in messages
    ]
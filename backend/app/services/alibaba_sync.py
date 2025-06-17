#!/usr/bin/env python3
"""Alibaba message synchronization service."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import PlatformAccount, Chat, Message, Profile
from app.models.message import MessageDirection, MessageStatus
from app.adapters.alibaba_production import AlibabaProductionAdapter
from app.adapters.alibaba_longrunning import AlibabaLongRunningAdapter
from app.db.base import SessionLocal

logger = logging.getLogger(__name__)


class AlibabaSyncService:
    """Service for syncing Alibaba messages."""
    
    def __init__(self, db: Session = None, use_longrunning: bool = True):
        self.db = db or SessionLocal()
        self.adapter = None
        self.use_longrunning = use_longrunning
        self._adapter_cache = {}  # Cache adapters by account ID
        
    async def sync_account_initial(self, account_id: str, days_back: int = 7) -> Dict[str, Any]:
        """Perform initial sync for an Alibaba account going back specified days."""
        try:
            logger.info(f"🔄 Starting initial sync for account {account_id}, {days_back} days back...")
            
            # Get the account
            account = self.db.query(PlatformAccount).filter(
                PlatformAccount.id == account_id
            ).first()
            
            if not account:
                return {"success": False, "error": f"Account {account_id} not found"}
            
            # Initialize adapter (use cached if available for long-running)
            if self.use_longrunning:
                if account_id not in self._adapter_cache:
                    self._adapter_cache[account_id] = AlibabaLongRunningAdapter(account)
                self.adapter = self._adapter_cache[account_id]
            else:
                self.adapter = AlibabaProductionAdapter(account)
            
            # Authenticate
            if not await self.adapter.authenticate():
                return {"success": False, "error": "Authentication failed"}
            
            # Get conversations from the past week
            conversations = await self.adapter.get_chats(max_age_days=days_back)
            
            sync_stats = {
                "conversations_processed": 0,
                "messages_synced": 0,
                "profiles_created": 0,
                "chats_created": 0
            }
            
            # Process each conversation
            for conv_data in conversations:
                try:
                    chat_result = await self._process_conversation(account, conv_data, days_back)
                    sync_stats["conversations_processed"] += 1
                    sync_stats["messages_synced"] += chat_result.get("messages_synced", 0)
                    sync_stats["profiles_created"] += chat_result.get("profiles_created", 0)
                    sync_stats["chats_created"] += chat_result.get("chats_created", 0)
                    
                except Exception as e:
                    logger.error(f"Error processing conversation {conv_data.get('id')}: {e}")
                    continue
            
            # Update account sync timestamp
            account.last_sync = datetime.utcnow()
            account.error_count = 0
            self.db.commit()
            
            logger.info(f"✅ Initial sync completed: {sync_stats}")
            return {"success": True, "stats": sync_stats}
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Initial sync failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
        finally:
            if self.adapter and not self.use_longrunning:
                await self.adapter.close()
    
    async def sync_account_incremental(self, account_id: str) -> Dict[str, Any]:
        """Perform incremental sync for new messages since last sync."""
        try:
            logger.info(f"🔄 Starting incremental sync for account {account_id}...")
            
            # Get the account
            account = self.db.query(PlatformAccount).filter(
                PlatformAccount.id == account_id
            ).first()
            
            if not account:
                return {"success": False, "error": f"Account {account_id} not found"}
            
            # Determine sync cutoff (last sync time or 1 hour ago as fallback)
            since = account.last_sync or (datetime.utcnow() - timedelta(hours=1))
            
            # Initialize adapter (use cached if available for long-running)
            if self.use_longrunning:
                if account_id not in self._adapter_cache:
                    self._adapter_cache[account_id] = AlibabaLongRunningAdapter(account)
                self.adapter = self._adapter_cache[account_id]
            else:
                self.adapter = AlibabaProductionAdapter(account)
            
            # Authenticate
            if not await self.adapter.authenticate():
                return {"success": False, "error": "Authentication failed"}
            
            sync_stats = {
                "conversations_checked": 0,
                "new_messages": 0,
                "updated_chats": 0
            }
            
            # Get existing chats for this account
            existing_chats = self.db.query(Chat).filter(
                Chat.account_id == account.id
            ).all()
            
            # Check each existing chat for new messages
            for chat in existing_chats:
                try:
                    # Get new messages since last sync
                    messages = await self.adapter.get_messages(
                        chat.platform_chat_id or str(chat.id), 
                        since=since
                    )
                    
                    sync_stats["conversations_checked"] += 1
                    
                    if messages:
                        message_result = await self._process_messages(chat, messages)
                        sync_stats["new_messages"] += message_result.get("messages_added", 0)
                        if message_result.get("messages_added", 0) > 0:
                            sync_stats["updated_chats"] += 1
                    
                except Exception as e:
                    logger.error(f"Error checking chat {chat.id}: {e}")
                    continue
            
            # Also check for any new conversations
            try:
                conversations = await self.adapter.get_chats(max_age_days=1)  # Only recent ones
                for conv_data in conversations:
                    # Check if this conversation already exists
                    existing_chat = self.db.query(Chat).filter(
                        and_(
                            Chat.account_id == account.id,
                            or_(
                                Chat.platform_chat_id == conv_data.get('id'),
                                Chat.id == conv_data.get('id')  # Fallback
                            )
                        )
                    ).first()
                    
                    if not existing_chat:
                        # New conversation - process it
                        chat_result = await self._process_conversation(account, conv_data, days_back=1)
                        sync_stats["new_messages"] += chat_result.get("messages_synced", 0)
                        if chat_result.get("chats_created", 0) > 0:
                            sync_stats["updated_chats"] += 1
            except Exception as e:
                logger.error(f"Error checking for new conversations: {e}")
            
            # Update account sync timestamp
            account.last_sync = datetime.utcnow()
            account.error_count = 0
            self.db.commit()
            
            logger.info(f"✅ Incremental sync completed: {sync_stats}")
            return {"success": True, "stats": sync_stats}
            
        except Exception as e:
            logger.error(f"❌ Incremental sync failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if self.adapter and not self.use_longrunning:
                await self.adapter.close()
    
    async def _process_conversation(self, account: PlatformAccount, conv_data: Dict[str, Any], days_back: int) -> Dict[str, Any]:
        """Process a single conversation and its messages."""
        stats = {
            "messages_synced": 0,
            "profiles_created": 0,
            "chats_created": 0
        }
        
        try:
            # Create or get profile for the conversation participant
            profile = await self._get_or_create_profile(account, conv_data)
            if profile:
                stats["profiles_created"] = 1
            
            # Create or get chat
            chat = await self._get_or_create_chat(account, profile, conv_data)
            if chat:
                stats["chats_created"] = 1
            
            # Get messages for this conversation
            since = datetime.utcnow() - timedelta(days=days_back)
            messages = await self.adapter.get_messages(conv_data.get('id'), since=since)
            
            if messages:
                message_result = await self._process_messages(chat, messages)
                stats["messages_synced"] = message_result.get("messages_added", 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            return stats
    
    async def _get_or_create_profile(self, account: PlatformAccount, conv_data: Dict[str, Any]) -> Optional[Profile]:
        """Get or create a profile for the conversation participant."""
        try:
            # Extract profile info from conversation data
            username = conv_data.get('title', '').strip()
            if not username:
                username = "Unknown User"
            
            # Look for existing profile for this account
            existing_profile = self.db.query(Profile).filter(
                and_(
                    Profile.account_id == account.id,
                    Profile.username == username
                )
            ).first()
            
            if existing_profile:
                return existing_profile
            
            # Create new profile
            profile = Profile(
                account_id=account.id,
                platform_user_id=conv_data.get('id', f"user_{username}"),
                username=username,
                display_name=username,
                platform_data=conv_data.get('platform_data', {}),
                last_seen=datetime.utcnow()
            )
            
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            
            logger.info(f"Created new profile: {username}")
            return profile
            
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            return None
    
    async def _get_or_create_chat(self, account: PlatformAccount, profile: Profile, conv_data: Dict[str, Any]) -> Optional[Chat]:
        """Get or create a chat for the conversation."""
        try:
            # Look for existing chat
            existing_chat = self.db.query(Chat).filter(
                and_(
                    Chat.account_id == account.id,
                    Chat.profile_id == profile.id
                )
            ).first()
            
            if existing_chat:
                # Update chat metadata
                existing_chat.platform_chat_id = conv_data.get('id')
                existing_chat.unread_count = conv_data.get('unread_count', 0)
                if conv_data.get('last_message_time'):
                    try:
                        existing_chat.last_message_at = datetime.fromisoformat(
                            conv_data['last_message_time'].replace('Z', '+00:00')
                        )
                    except:
                        pass
                self.db.commit()
                return existing_chat
            
            # Create new chat
            chat = Chat(
                account_id=account.id,
                profile_id=profile.id,
                platform_chat_id=conv_data.get('id'),
                unread_count=conv_data.get('unread_count', 0),
                is_active=True
            )
            
            # Set last message time if available
            if conv_data.get('last_message_time'):
                try:
                    chat.last_message_at = datetime.fromisoformat(
                        conv_data['last_message_time'].replace('Z', '+00:00')
                    )
                except:
                    pass
            
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
            
            logger.info(f"Created new chat: {profile.username}")
            return chat
            
        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            return None
    
    async def _process_messages(self, chat: Chat, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process messages for a chat."""
        stats = {"messages_added": 0}
        
        try:
            for msg_data in messages:
                # Check if message already exists
                existing_message = self.db.query(Message).filter(
                    and_(
                        Message.chat_id == chat.id,
                        Message.platform_message_id == msg_data.get('id')
                    )
                ).first()
                
                if existing_message:
                    continue  # Skip existing messages
                
                # Create new message
                message = Message(
                    chat_id=chat.id,
                    platform_message_id=msg_data.get('id'),
                    content=msg_data.get('content', ''),
                    content_type=msg_data.get('message_type', 'text'),
                    direction=MessageDirection.INCOMING if msg_data.get('direction') == 'incoming' else MessageDirection.OUTGOING,
                    status=MessageStatus.DELIVERED,
                    is_reply=msg_data.get('is_reply', False),
                    reply_to_content=msg_data.get('reply_to_content')
                )
                
                # Set timestamp
                if msg_data.get('timestamp'):
                    try:
                        message.platform_timestamp = datetime.fromisoformat(
                            msg_data['timestamp'].replace('Z', '+00:00')
                        )
                    except:
                        message.platform_timestamp = datetime.utcnow()
                else:
                    message.platform_timestamp = datetime.utcnow()
                
                self.db.add(message)
                stats["messages_added"] += 1
                
                # Update chat's last message time (ensure timezone-aware comparison)
                if message.platform_timestamp:
                    if not chat.last_message_at:
                        chat.last_message_at = message.platform_timestamp
                    else:
                        # Ensure both are timezone-aware for comparison
                        chat_time = chat.last_message_at
                        msg_time = message.platform_timestamp
                        
                        # Make timezone-aware if needed
                        if chat_time.tzinfo is None:
                            chat_time = chat_time.replace(tzinfo=timezone.utc)
                        if msg_time.tzinfo is None:
                            msg_time = msg_time.replace(tzinfo=timezone.utc)
                        
                        if msg_time > chat_time:
                            chat.last_message_at = message.platform_timestamp
            
            self.db.commit()
            
            if stats["messages_added"] > 0:
                logger.info(f"Added {stats['messages_added']} new messages to chat {chat.id}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing messages: {e}")
            return stats
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
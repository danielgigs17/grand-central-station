from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import json

from app.adapters.base import PlatformAdapter, BrowserAdapter


class AlibabaAdapter(PlatformAdapter):
    """Adapter for Alibaba messaging using reverse-engineered API."""
    
    BASE_URL = "https://message.alibaba.com"
    API_BASE_URL = "https://message.alibaba.com/api"
    LOGIN_URL = "https://login.alibaba.com"
    
    def __init__(self, account):
        super().__init__(account)
        self.csrf_token = self.account.session_data.get("csrf_token") if self.account.session_data else None
        self.user_id = self.account.session_data.get("user_id") if self.account.session_data else None
        
        if self.csrf_token:
            self.client.headers["X-CSRF-Token"] = self.csrf_token
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get Alibaba-specific headers."""
        headers = super()._get_default_headers()
        headers.update({
            "Referer": self.BASE_URL,
            "Origin": self.BASE_URL,
            "X-Requested-With": "XMLHttpRequest",
        })
        return headers
    
    async def authenticate(self) -> bool:
        """Authenticate with Alibaba messaging system."""
        try:
            # Step 1: Get login page to extract CSRF token
            login_response = self.client.get(f"{self.LOGIN_URL}/login")
            if login_response.status_code != 200:
                return False
            
            # Extract CSRF token from login page (implementation depends on actual HTML structure)
            csrf_token = self._extract_csrf_token(login_response.text)
            if not csrf_token:
                self.logger.error("Failed to extract CSRF token")
                return False
            
            self.csrf_token = csrf_token
            self.client.headers["X-CSRF-Token"] = csrf_token
            
            # Step 2: Perform login
            login_data = {
                "loginId": self.account.username,
                "password": self.account.password,
                "csrf_token": csrf_token,
            }
            
            response = self.client.post(
                f"{self.LOGIN_URL}/authenticate",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                if auth_data.get("success"):
                    self.user_id = auth_data.get("userId")
                    self.account.session_data = {
                        "csrf_token": self.csrf_token,
                        "user_id": self.user_id,
                        "cookies": dict(self.client.cookies),
                    }
                    self._save_cookies()
                    return True
                    
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            
        return False
    
    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """Extract CSRF token from HTML response."""
        # Implementation will depend on actual Alibaba HTML structure
        # Common patterns: meta tag, hidden input, script variable
        import re
        
        # Try meta tag
        meta_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        if meta_match:
            return meta_match.group(1)
        
        # Try script variable
        script_match = re.search(r'window\.csrfToken\s*=\s*["\']([^"\']+)', html)
        if script_match:
            return script_match.group(1)
        
        return None
    
    async def get_chats(self) -> List[Dict[str, Any]]:
        """Get list of conversations."""
        try:
            response = self.client.get(f"{self.API_BASE_URL}/conversations")
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("conversations", [])
                
                # Normalize conversation data
                return [
                    {
                        "id": conv.get("conversationId"),
                        "title": conv.get("title") or conv.get("participantName"),
                        "last_message": conv.get("lastMessage", {}).get("content"),
                        "last_message_time": conv.get("lastMessage", {}).get("timestamp"),
                        "unread_count": conv.get("unreadCount", 0),
                        "participants": conv.get("participants", []),
                        "platform_data": conv,  # Store original data
                    }
                    for conv in conversations
                ]
        except Exception as e:
            self.logger.error(f"Failed to get chats: {e}")
        return []
    
    async def get_messages(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages for a conversation."""
        try:
            params = {"conversationId": chat_id, "limit": 50}
            if since:
                params["since"] = since.isoformat()
                
            response = self.client.get(f"{self.API_BASE_URL}/messages", params=params)
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                # Normalize message data
                return [
                    {
                        "id": msg.get("messageId"),
                        "content": msg.get("content") or msg.get("text"),
                        "sender_id": msg.get("senderId"),
                        "sender_name": msg.get("senderName"),
                        "timestamp": msg.get("timestamp"),
                        "message_type": msg.get("type", "text"),
                        "media_urls": msg.get("attachments", []),
                        "platform_data": msg,  # Store original data
                    }
                    for msg in messages
                ]
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
        return []
    
    async def send_message(self, chat_id: str, content: str, media: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send a message."""
        try:
            payload = {
                "conversationId": chat_id,
                "content": content,
                "type": "text",
            }
            
            if media:
                # Upload media first
                media_ids = await self._upload_media(media)
                if media_ids:
                    payload["attachments"] = media_ids
                    payload["type"] = "media"
                
            response = self.client.post(f"{self.API_BASE_URL}/messages", json=payload)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
        return {}
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile."""
        try:
            response = self.client.get(f"{self.API_BASE_URL}/users/{user_id}")
            if response.status_code == 200:
                profile = response.json()
                
                return {
                    "platform_user_id": user_id,
                    "username": profile.get("username") or profile.get("displayName"),
                    "company_name": profile.get("companyName"),
                    "title": profile.get("title"),
                    "location": profile.get("location"),
                    "bio": profile.get("description"),
                    "platform_data": {
                        "member_level": profile.get("memberLevel"),
                        "verification_status": profile.get("isVerified"),
                        "response_rate": profile.get("responseRate"),
                        "response_time": profile.get("avgResponseTime"),
                        "transaction_count": profile.get("transactionCount"),
                        "years_on_platform": profile.get("yearsOnPlatform"),
                    },
                    "profile_photo_url": profile.get("avatarUrl"),
                    "contact_info": {
                        "email": profile.get("email"),
                        "phone": profile.get("phone"),
                        "website": profile.get("website"),
                    },
                }
        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
        return {}
    
    async def download_media(self, url: str, save_path: str) -> bool:
        """Download media file."""
        try:
            response = self.client.get(url)
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                return True
        except Exception as e:
            self.logger.error(f"Failed to download media: {e}")
        return False
    
    async def _upload_media(self, media_paths: List[str]) -> List[str]:
        """Upload media files and return media IDs."""
        media_ids = []
        for path in media_paths:
            try:
                with open(path, "rb") as f:
                    files = {"file": f}
                    response = self.client.post(f"{self.API_BASE_URL}/upload", files=files)
                    if response.status_code == 200:
                        data = response.json()
                        media_ids.append(data.get("mediaId"))
            except Exception as e:
                self.logger.error(f"Failed to upload media {path}: {e}")
        return media_ids


class AlibabaBrowserAdapter(BrowserAdapter):
    """Browser automation fallback for Alibaba messaging."""
    
    BASE_URL = "https://message.alibaba.com"
    LOGIN_URL = "https://login.alibaba.com"
    
    async def authenticate(self) -> bool:
        """Authenticate using browser automation."""
        try:
            await self.init_browser()
            await self.page.goto(f"{self.LOGIN_URL}/login")
            
            # Fill login form
            await self.page.fill('input[name="loginId"]', self.account.username)
            await self.page.fill('input[name="password"]', self.account.password)
            
            # Handle captcha if present
            captcha_element = await self.page.query_selector('.captcha-image')
            if captcha_element:
                self.logger.warning("Captcha detected - manual intervention required")
                # Could implement OCR or manual intervention here
                return False
            
            # Submit login
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_navigation()
            
            # Check if login successful
            if "dashboard" in self.page.url or "message" in self.page.url:
                await self.save_browser_state()
                return True
                
        except Exception as e:
            self.logger.error(f"Browser authentication failed: {e}")
            
        return False
    
    async def get_chats(self) -> List[Dict[str, Any]]:
        """Get conversations using DOM extraction."""
        try:
            await self.page.goto(f"{self.BASE_URL}/conversations")
            await self.page.wait_for_selector('.conversation-list')
            
            # Extract conversation data from DOM
            conversations = await self.page.evaluate("""
                () => {
                    const convElements = document.querySelectorAll('.conversation-item');
                    return Array.from(convElements).map(el => ({
                        id: el.dataset.conversationId,
                        title: el.querySelector('.conversation-title')?.textContent,
                        lastMessage: el.querySelector('.last-message')?.textContent,
                        unreadCount: parseInt(el.querySelector('.unread-badge')?.textContent || '0'),
                    }));
                }
            """)
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"Failed to get chats via browser: {e}")
        return []
    
    async def get_messages(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages using DOM extraction."""
        try:
            await self.page.goto(f"{self.BASE_URL}/conversation/{chat_id}")
            await self.page.wait_for_selector('.message-list')
            
            # Extract messages from DOM
            messages = await self.page.evaluate("""
                () => {
                    const msgElements = document.querySelectorAll('.message-item');
                    return Array.from(msgElements).map(el => ({
                        id: el.dataset.messageId,
                        content: el.querySelector('.message-content')?.textContent,
                        senderId: el.dataset.senderId,
                        timestamp: el.dataset.timestamp,
                        messageType: el.dataset.messageType || 'text',
                    }));
                }
            """)
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to get messages via browser: {e}")
        return []
    
    async def send_message(self, chat_id: str, content: str, media: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send message using browser automation."""
        try:
            await self.page.goto(f"{self.BASE_URL}/conversation/{chat_id}")
            await self.page.wait_for_selector('.message-input')
            
            # Fill message content
            await self.page.fill('.message-input', content)
            
            # Handle media upload if needed
            if media:
                for media_path in media:
                    await self.page.set_input_files('.file-upload-input', media_path)
            
            # Send message
            await self.page.click('.send-button')
            await self.page.wait_for_selector('.message-item:last-child')
            
            return {"success": True}
            
        except Exception as e:
            self.logger.error(f"Failed to send message via browser: {e}")
        return {}
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get profile using DOM extraction."""
        try:
            await self.page.goto(f"{self.BASE_URL}/profile/{user_id}")
            await self.page.wait_for_selector('.profile-container')
            
            # Extract profile data from DOM
            profile = await self.page.evaluate("""
                () => {
                    return {
                        username: document.querySelector('.profile-name')?.textContent,
                        companyName: document.querySelector('.company-name')?.textContent,
                        title: document.querySelector('.profile-title')?.textContent,
                        location: document.querySelector('.profile-location')?.textContent,
                        bio: document.querySelector('.profile-bio')?.textContent,
                        avatarUrl: document.querySelector('.profile-avatar')?.src,
                    };
                }
            """)
            
            return {
                "platform_user_id": user_id,
                **profile,
                "platform_data": profile,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get profile via browser: {e}")
        return {}
    
    async def download_media(self, url: str, save_path: str) -> bool:
        """Download media via browser."""
        try:
            response = await self.page.context.request.get(url)
            if response.ok:
                with open(save_path, "wb") as f:
                    f.write(await response.body())
                return True
        except Exception as e:
            self.logger.error(f"Failed to download media via browser: {e}")
        return False
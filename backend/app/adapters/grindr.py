from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

from app.adapters.base import PlatformAdapter


class GrindrAdapter(PlatformAdapter):
    """Adapter for Grindr using reverse-engineered API."""
    
    BASE_URL = "https://grindr.mobi/v4"
    
    def __init__(self, account):
        super().__init__(account)
        self.auth_token = self.account.session_data.get("auth_token") if self.account.session_data else None
        
        if self.auth_token:
            self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
    
    async def authenticate(self) -> bool:
        """Authenticate with Grindr API."""
        try:
            response = self.client.post(
                f"{self.BASE_URL}/sessions",
                json={
                    "email": self.account.username,
                    "password": self.account.password,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("sessionId")
                self.account.session_data = {
                    "auth_token": self.auth_token,
                    "profile_id": data.get("profileId"),
                }
                self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
                return True
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            
        return False
    
    async def get_chats(self) -> List[Dict[str, Any]]:
        """Get list of conversations."""
        try:
            response = self.client.get(f"{self.BASE_URL}/conversations")
            if response.status_code == 200:
                return response.json().get("conversations", [])
        except Exception as e:
            self.logger.error(f"Failed to get chats: {e}")
        return []
    
    async def get_messages(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages for a conversation."""
        try:
            params = {"conversationId": chat_id}
            if since:
                params["after"] = since.isoformat()
                
            response = self.client.get(f"{self.BASE_URL}/messages", params=params)
            if response.status_code == 200:
                return response.json().get("messages", [])
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
        return []
    
    async def send_message(self, chat_id: str, content: str, media: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send a message."""
        try:
            payload = {
                "conversationId": chat_id,
                "text": content,
            }
            
            if media:
                # Handle media upload separately
                payload["mediaIds"] = await self._upload_media(media)
                
            response = self.client.post(f"{self.BASE_URL}/messages", json=payload)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
        return {}
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with Grindr-specific fields."""
        try:
            response = self.client.get(f"{self.BASE_URL}/profiles/{user_id}")
            if response.status_code == 200:
                profile = response.json()
                
                # Extract Grindr-specific fields
                return {
                    "platform_user_id": user_id,
                    "username": profile.get("displayName"),
                    "age": profile.get("age"),
                    "bio": profile.get("aboutMe"),
                    "location": profile.get("distance"),
                    "platform_data": {
                        "position": profile.get("position"),
                        "race": profile.get("ethnicity"),
                        "weight": profile.get("weight"),
                        "height": profile.get("height"),
                        "tribes": profile.get("tribes", []),
                        "looking_for": profile.get("lookingFor", []),
                        "stats": {
                            "hiv_status": profile.get("hivStatus"),
                            "last_tested": profile.get("lastTestedDate"),
                        },
                        "taps_received": profile.get("tapsReceived", 0),
                    },
                    "profile_photo_url": profile.get("profilePhotoUrl"),
                    "albums": profile.get("albums", []),
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
        # Implementation for media upload
        return []
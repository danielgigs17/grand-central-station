from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import httpx
import json
import logging

from app.models import PlatformAccount


class PlatformAdapter(ABC):
    """Base class for platform adapters."""
    
    def __init__(self, account: PlatformAccount):
        self.account = account
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.client = httpx.Client(
            headers=self._get_default_headers(),
            cookies=self._load_cookies(),
            timeout=30.0,
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    
    def _load_cookies(self) -> Dict[str, str]:
        """Load cookies from account session data."""
        if self.account.session_data and "cookies" in self.account.session_data:
            return self.account.session_data["cookies"]
        return {}
    
    def _save_cookies(self):
        """Save cookies to account session data."""
        cookies = {k: v for k, v in self.client.cookies.items()}
        if not self.account.session_data:
            self.account.session_data = {}
        self.account.session_data["cookies"] = cookies
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform."""
        pass
    
    @abstractmethod
    async def get_chats(self) -> List[Dict[str, Any]]:
        """Get list of chats/conversations."""
        pass
    
    @abstractmethod
    async def get_messages(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages for a specific chat."""
        pass
    
    @abstractmethod
    async def send_message(self, chat_id: str, content: str, media: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send a message to a chat."""
        pass
    
    @abstractmethod
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get profile information for a user."""
        pass
    
    @abstractmethod
    async def download_media(self, url: str, save_path: str) -> bool:
        """Download media file from platform."""
        pass
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()


class BrowserAdapter(PlatformAdapter):
    """Base class for adapters that need browser automation."""
    
    def __init__(self, account: PlatformAccount):
        super().__init__(account)
        self.page = None
        self.browser = None
    
    async def init_browser(self):
        """Initialize Playwright browser."""
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        context = await self.browser.new_context(
            user_agent=self._get_default_headers()["User-Agent"],
            viewport={"width": 1280, "height": 720},
        )
        
        # Load cookies if available
        if self.account.session_data and "cookies" in self.account.session_data:
            await context.add_cookies(self.account.session_data["cookies"])
            
        self.page = await context.new_page()
    
    async def save_browser_state(self):
        """Save browser cookies and local storage."""
        if self.page:
            cookies = await self.page.context.cookies()
            self.account.session_data["cookies"] = [
                {k: v for k, v in cookie.items() if k in ["name", "value", "domain", "path"]}
                for cookie in cookies
            ]
    
    async def close(self):
        """Close browser and HTTP client."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        super().close()
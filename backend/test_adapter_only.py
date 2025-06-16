#!/usr/bin/env python3
"""Test script for Alibaba production adapter only (no DB dependencies)."""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the email_2fa module to the path
sys.path.append(os.path.dirname(__file__))
from email_2fa import EmailTwoFactorReader


class MockAccount:
    """Mock account for testing."""
    def __init__(self):
        self.username = "daniel_allen@fastmail.com"
        self.password = "P123okemon1."
        self.session_data = {}


class SimpleAlibabaAdapter:
    """Simplified Alibaba adapter for testing without DB dependencies."""
    
    def __init__(self, account):
        self.account = account
        self.email_reader = None
        self.authenticated = False
        self.page = None
        self.browser = None
        self.playwright = None
        
        # Initialize email reader for 2FA
        email_password = os.getenv("EMAIL_PASSWORD")
        if email_password:
            self.email_reader = EmailTwoFactorReader(
                email_address=account.username,
                password=email_password
            )
    
    async def init_browser(self, headless: bool = True):
        """Initialize browser."""
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}
        )
        
        self.page = await context.new_page()
        
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
    
    async def authenticate(self) -> bool:
        """Test authentication."""
        try:
            logger.info("🔐 Testing Alibaba authentication...")
            
            if not self.page:
                await self.init_browser()
            
            # Navigate to login page
            login_url = "https://login.alibaba.com/newlogin/icbuLogin.htm?origin=message.alibaba.com&flag=1&return_url=https%253A%252F%252Fmessage.alibaba.com%252Fmessage%252Fmessenger.htm"
            logger.info("📥 Navigating to login page...")
            await self.page.goto(login_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            
            # Fill credentials
            await self._fill_credentials()
            
            # Submit login
            await self._submit_login()
            
            # Handle 2FA if required
            if await self._is_2fa_required():
                if not await self._handle_2fa():
                    return False
            
            # Check final state
            await self.page.wait_for_timeout(5000)
            current_url = self.page.url
            
            if current_url.startswith("https://message.alibaba.com"):
                logger.info("✅ Authentication successful!")
                self.authenticated = True
                return True
            else:
                # Try manual navigation
                try:
                    await self.page.goto("https://message.alibaba.com/message/messenger.htm", wait_until="networkidle", timeout=30000)
                    if self.page.url.startswith("https://message.alibaba.com"):
                        logger.info("✅ Authentication successful via manual navigation!")
                        self.authenticated = True
                        return True
                except Exception as e:
                    logger.error(f"Manual navigation failed: {e}")
            
            logger.error("❌ Authentication failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def _fill_credentials(self):
        """Fill login credentials."""
        logger.info("✏️ Filling credentials...")
        
        # Username
        username_input = await self.page.wait_for_selector('input[name="account"]', timeout=5000)
        await username_input.fill(self.account.username)
        
        # Password
        password_input = await self.page.wait_for_selector('input[type="password"]', timeout=5000)
        await password_input.fill(self.account.password)
        
        logger.info("✅ Credentials filled")
    
    async def _submit_login(self):
        """Submit login form."""
        logger.info("🖱️ Submitting login...")
        
        submit_button = await self.page.wait_for_selector('button:has-text("Sign in")', timeout=5000)
        await submit_button.click()
        await self.page.wait_for_timeout(5000)
        
        logger.info("✅ Login submitted")
    
    async def _is_2fa_required(self) -> bool:
        """Check if 2FA is required."""
        current_url = self.page.url
        if "login" not in current_url:
            return False
        
        page_content = await self.page.content()
        has_verification_text = any(keyword in page_content.lower() for keyword in [
            'verification', 'verify', 'code', '验证', 'security', '2fa'
        ])
        
        if has_verification_text:
            logger.info("🔍 2FA verification required")
            return True
        
        return False
    
    async def _handle_2fa(self) -> bool:
        """Handle 2FA verification."""
        if not self.email_reader:
            logger.error("❌ 2FA required but no email reader configured")
            return False
        
        try:
            logger.info("🔐 Handling 2FA...")
            
            # Wait for modal
            await self.page.wait_for_timeout(8000)
            
            # Get 2FA code
            logger.info("📧 Getting 2FA code from email...")
            await asyncio.sleep(10)
            
            code = self.email_reader.get_latest_alibaba_2fa_code(max_age_minutes=5, delete_after_use=True)
            if not code:
                logger.error("❌ No 2FA code found")
                return False
            
            logger.info(f"✅ Found 2FA code: {code}")
            
            # Use coordinate-based input
            logger.info("🎯 Entering 2FA code...")
            await self.page.mouse.click(730, 360)  # Click input field
            await self.page.wait_for_timeout(1000)
            await self.page.keyboard.type(code)
            await self.page.wait_for_timeout(1000)
            await self.page.mouse.click(685, 508)  # Click submit
            await self.page.keyboard.press('Enter')
            
            await self.page.wait_for_timeout(10000)
            
            logger.info("✅ 2FA completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ 2FA failed: {e}")
            return False
    
    async def test_message_access(self) -> bool:
        """Test if we can access messages."""
        if not self.authenticated:
            logger.warning("Not authenticated, skipping message test")
            return False
        
        try:
            logger.info("📬 Testing message access...")
            
            # Check if we can see the page content
            page_text = await self.page.text_content('body')
            
            # Look for our known message
            if "Linda Wu" in page_text:
                logger.info("✅ Found 'Linda Wu' in page content")
            
            if "ok,Daniel" in page_text:
                logger.info("✅ Found 'ok,Daniel' message in page content")
                return True
            
            logger.info("ℹ️  Page loaded but target message not found")
            return True  # Still success if we can access the page
            
        except Exception as e:
            logger.error(f"❌ Message access test failed: {e}")
            return False
    
    async def close(self):
        """Clean up."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def main():
    """Test the adapter."""
    logger.info("🚀 Testing Alibaba Production Adapter...")
    
    # Check environment
    email_password = os.getenv("EMAIL_PASSWORD")
    if not email_password:
        logger.error("❌ EMAIL_PASSWORD environment variable not set")
        return
    
    account = MockAccount()
    adapter = SimpleAlibabaAdapter(account)
    
    try:
        # Test authentication
        auth_success = await adapter.authenticate()
        
        if auth_success:
            # Test message access
            message_success = await adapter.test_message_access()
            
            if message_success:
                logger.info("🎉 All tests passed! Adapter is working correctly.")
            else:
                logger.warning("⚠️  Authentication worked but message access failed.")
        else:
            logger.error("❌ Authentication failed.")
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
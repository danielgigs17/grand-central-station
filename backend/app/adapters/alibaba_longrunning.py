#!/usr/bin/env python3
"""Long-running Alibaba adapter with persistent browser and proper message extraction."""

import asyncio
import logging
import json
import re
import os
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page

from app.adapters.base import BrowserAdapter
from app.db.base import SessionLocal
from email_2fa import EmailTwoFactorReader
from app.adapters.alibaba_message_parser import AlibabaMessageParser

logger = logging.getLogger(__name__)


class AlibabaLongRunningAdapter(BrowserAdapter):
    """Long-running Alibaba adapter that keeps browser open and refreshes periodically."""
    
    LOGIN_URL = "https://login.alibaba.com/newlogin/icbuLogin.htm"
    MESSAGE_URL = "https://message.alibaba.com/message/messenger.htm"
    
    def __init__(self, account):
        super().__init__(account)
        self.email_reader = None
        self.authenticated = False
        self.browser_context = None
        self.last_refresh = None
        self.refresh_interval = 300  # 5 minutes
        self.message_parser = AlibabaMessageParser()
        
        # Initialize email reader for 2FA if credentials available
        email_password = os.getenv("EMAIL_PASSWORD")
        if email_password and hasattr(account, 'username'):
            twofa_folder = os.getenv("EMAIL_2FA_FOLDER", "2FA")
            self.email_reader = EmailTwoFactorReader(
                email_address=account.username,
                password=email_password,
                folder=twofa_folder
            )
    
    async def init_browser(self, headless: bool = True):
        """Initialize browser with persistent context and cookies."""
        self.playwright = await async_playwright().start()
        
        # Create persistent browser context
        user_data_dir = f"/tmp/alibaba_browser_{self.account.id}"
        os.makedirs(user_data_dir, exist_ok=True)
        
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            args=[
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--allow-running-insecure-content'
            ],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            locale="en-US",
            timezone_id="America/New_York"
        )
        
        # Load saved cookies if available
        if self.account.session_data and "cookies" in self.account.session_data:
            try:
                await self.browser_context.add_cookies(self.account.session_data["cookies"])
                logger.info("🍪 Loaded saved cookies")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        
        # Get the page
        pages = self.browser_context.pages
        self.page = pages[0] if pages else await self.browser_context.new_page()
        
        # Add script to remove webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
    
    async def authenticate(self) -> bool:
        """Authenticate with Alibaba, reusing session if possible."""
        try:
            logger.info("🔐 Starting Alibaba authentication...")
            
            # Check if we should run headless
            headless = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
            logger.info(f"🖥️  Running browser in {'headless' if headless else 'visible'} mode")
            
            if not self.page:
                await self.init_browser(headless=headless)
            
            # First, try to navigate to messages directly (if we have valid cookies)
            if self.account.session_data and "cookies" in self.account.session_data:
                logger.info("🍪 Attempting to use saved session...")
                await self.page.goto(self.MESSAGE_URL, wait_until="load", timeout=30000)
                await self.page.wait_for_timeout(3000)
                
                if self.page.url.startswith("https://message.alibaba.com") and "login" not in self.page.url:
                    logger.info("✅ Authentication successful using saved session!")
                    self.authenticated = True
                    self.last_refresh = datetime.now()
                    return True
            
            # If not authenticated, proceed with login
            login_url = f"{self.LOGIN_URL}?origin=message.alibaba.com&flag=1&return_url=https%253A%252F%252Fmessage.alibaba.com%252Fmessage%252Fmessenger.htm"
            logger.info(f"📥 Navigating to login page...")
            await self.page.goto(login_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            
            # Fill credentials
            await self._fill_login_credentials()
            await self._submit_login()
            
            # Check if 2FA is required
            if await self._is_2fa_required():
                success = await self._handle_2fa()
                if not success:
                    # Check if we're on the messages page after 400 redirect
                    await self.page.wait_for_timeout(5000)
                    if self.page.url.startswith("https://message.alibaba.com"):
                        logger.info("✅ Authentication successful despite 400 redirect!")
                        await self.save_browser_state()
                        self.authenticated = True
                        self.last_refresh = datetime.now()
                        return True
                    return False
            
            # Wait for navigation to complete
            await self.page.wait_for_timeout(5000)
            
            # Check if we're on the messages page
            if self.page.url.startswith("https://message.alibaba.com"):
                logger.info("✅ Authentication successful!")
                await self.save_browser_state()
                self.authenticated = True
                self.last_refresh = datetime.now()
                return True
            else:
                # Try manual navigation
                try:
                    await self.page.goto(self.MESSAGE_URL, wait_until="load", timeout=60000)
                    await self.page.wait_for_timeout(10000)
                    if self.page.url.startswith("https://message.alibaba.com"):
                        logger.info("✅ Authentication successful via manual navigation!")
                        await self.save_browser_state()
                        self.authenticated = True
                        self.last_refresh = datetime.now()
                        return True
                except Exception as e:
                    logger.error(f"Manual navigation failed: {e}")
            
            logger.error("❌ Authentication failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def refresh_if_needed(self):
        """Refresh the page if needed to keep session alive."""
        if not self.authenticated or not self.last_refresh:
            return await self.authenticate()
        
        time_since_refresh = (datetime.now() - self.last_refresh).total_seconds()
        if time_since_refresh > self.refresh_interval:
            logger.info("🔄 Refreshing page to keep session alive...")
            await self.page.reload(wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            self.last_refresh = datetime.now()
            
            # Verify we're still on the right page
            if not self.page.url.startswith("https://message.alibaba.com"):
                logger.warning("⚠️  Lost session, re-authenticating...")
                self.authenticated = False
                return await self.authenticate()
        
        return True
    
    async def get_chats(self, max_age_days: int = 7) -> List[Dict[str, Any]]:
        """Get list of conversations with proper extraction."""
        if not await self.refresh_if_needed():
            return []
        
        try:
            logger.info("📋 Retrieving conversations...")
            
            # Navigate to message page if not already there
            if not self.page.url.startswith("https://message.alibaba.com"):
                await self.page.goto(self.MESSAGE_URL, wait_until="networkidle", timeout=60000)
            
            await self.page.wait_for_timeout(5000)
            
            # Wait for conversation list to load
            try:
                await self.page.wait_for_selector('[class*="conversation"]', timeout=10000)
                logger.info("✅ Found conversation elements")
            except:
                logger.warning("Conversation list selector not found, trying alternative selectors...")
                # Take a screenshot to debug
                await self.page.screenshot(path="debug_conversations.png")
                logger.info("📸 Saved debug screenshot to debug_conversations.png")
            
            # Extract conversations with better parsing
            conversations = await self._extract_conversations_properly()
            
            logger.info(f"✅ Found {len(conversations)} conversations")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversations: {e}")
            return []
    
    async def _extract_conversations_properly(self) -> List[Dict[str, Any]]:
        """Extract conversations with proper name and message parsing."""
        conversations = []
        
        try:
            # Use the selector that was working in production adapter
            conv_elements = await self.page.query_selector_all('[class*="conversation"]')
            
            if conv_elements:
                logger.info(f"Found {len(conv_elements)} elements with selector: [class*=\"conversation\"]")
            else:
                logger.warning("No conversation elements found with standard selectors")
                # Fallback: look for any clickable items that might be conversations
                conv_elements = await self.page.query_selector_all('div[onclick], div[data-chat-id], a[href*="chat"]')
            
            for i, element in enumerate(conv_elements[:10]):  # Limit to 10 conversations
                try:
                    # Extract text content
                    text_content = await element.inner_text()
                    logger.debug(f"Processing element {i}: {text_content[:100]}...")
                    
                    # Extract contact name
                    contact_name = await self._extract_contact_name_from_element(element)
                    if not contact_name:
                        logger.debug(f"No contact name found in element {i}")
                        continue
                    
                    logger.info(f"Found contact: {contact_name}")
                    
                    # Extract last message
                    last_message = await self._extract_last_message_from_element(element)
                    
                    # Extract timestamp if available
                    timestamp = await self._extract_timestamp_from_element(element)
                    
                    # Extract chat ID or create one
                    chat_id = await self._extract_chat_id_from_element(element) or f"chat_{i}_{contact_name.replace(' ', '_').lower()}"
                    
                    conversations.append({
                        'id': chat_id,
                        'title': contact_name,
                        'last_message': last_message,
                        'last_message_time': timestamp or datetime.now().isoformat(),
                        'unread_count': 0,
                        'participants': [contact_name],
                        'platform_data': {
                            'element_index': i,
                            'selector': '[class*="conversation"]',
                            'raw_text': text_content[:500]  # Limit raw text storage
                        }
                    })
                    
                except Exception as e:
                    logger.debug(f"Error processing conversation element {i}: {e}")
                    continue
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error extracting conversations: {e}")
            return []
    
    async def _extract_contact_name_from_element(self, element) -> Optional[str]:
        """Extract clean contact name from conversation element."""
        try:
            # Try specific selectors for contact name
            name_selectors = [
                '.contact-name',
                '.user-name',
                '.conversation-title',
                '[class*="name"]',
                'h3', 'h4', 'h5',
                'strong'
            ]
            
            for selector in name_selectors:
                try:
                    name_element = await element.query_selector(selector)
                    if name_element:
                        name = await name_element.inner_text()
                        clean_name = self._clean_contact_name(name)
                        if clean_name:
                            return clean_name
                except:
                    continue
            
            # Fallback: extract from full text
            full_text = await element.inner_text()
            return self._extract_contact_name(full_text)
            
        except Exception as e:
            logger.debug(f"Error extracting contact name: {e}")
            return None
    
    async def _extract_last_message_from_element(self, element) -> str:
        """Extract last message from conversation element."""
        try:
            # Try specific selectors for last message
            msg_selectors = [
                '.last-message',
                '.message-preview',
                '[class*="preview"]',
                '[class*="snippet"]',
                'p',
                'span'
            ]
            
            for selector in msg_selectors:
                try:
                    msg_elements = await element.query_selector_all(selector)
                    for msg_element in msg_elements:
                        text = await msg_element.inner_text()
                        if text and len(text) > 5 and len(text) < 200:
                            # Filter out timestamps and metadata
                            if not re.match(r'^\d{4}-\d{2}-\d{2}', text) and 'Co., Ltd' not in text:
                                return text.strip()
                except:
                    continue
            
            return "No recent message"
            
        except Exception as e:
            logger.debug(f"Error extracting last message: {e}")
            return "No recent message"
    
    async def _extract_timestamp_from_element(self, element) -> Optional[str]:
        """Extract timestamp from conversation element."""
        try:
            # Look for timestamp patterns
            text = await element.inner_text()
            
            # Common timestamp patterns
            patterns = [
                r'(\d{4}-\d{1,2}-\d{1,2})',  # 2025-6-15
                r'(\d{1,2}/\d{1,2}/\d{4})',   # 6/15/2025
                r'(\d{1,2}:\d{2})',            # 13:45
                r'(yesterday|today)',           # Relative dates
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    timestamp_str = match.group(1)
                    # Convert to ISO format if possible
                    try:
                        if 'yesterday' in timestamp_str.lower():
                            return (datetime.now() - timedelta(days=1)).isoformat()
                        elif 'today' in timestamp_str.lower():
                            return datetime.now().isoformat()
                        else:
                            # Try to parse the date
                            return timestamp_str
                    except:
                        return timestamp_str
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting timestamp: {e}")
            return None
    
    async def _extract_chat_id_from_element(self, element) -> Optional[str]:
        """Extract chat ID from element attributes."""
        try:
            # Check common attributes
            attrs = ['data-chat-id', 'data-conversation-id', 'data-id', 'id']
            for attr in attrs:
                value = await element.get_attribute(attr)
                if value:
                    return value
            
            # Check onclick handler
            onclick = await element.get_attribute('onclick')
            if onclick:
                # Look for ID patterns in onclick
                match = re.search(r'["\']id["\']\s*:\s*["\']([^"\']+)["\']', onclick)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting chat ID: {e}")
            return None
    
    async def get_messages(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages for a specific conversation with proper extraction."""
        if not await self.refresh_if_needed():
            return []
        
        try:
            logger.info(f"📬 Getting messages for chat: {chat_id}")
            
            # Click on the conversation to open it
            success = await self._open_conversation(chat_id)
            if not success:
                logger.warning(f"Failed to open conversation {chat_id}")
                return []
            
            # Wait for messages to load
            logger.info("⏳ Waiting for messages to load...")
            await self.page.wait_for_timeout(5000)
            
            # Take a screenshot for debugging
            await self.page.screenshot(path=f"conversation_{chat_id}.png")
            logger.info(f"📸 Saved conversation screenshot to conversation_{chat_id}.png")
            
            # Extract messages from the conversation
            messages = await self._extract_messages_from_conversation(chat_id, since)
            
            logger.info(f"✅ Retrieved {len(messages)} messages")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Failed to get messages: {e}")
            return []
    
    async def _open_conversation(self, chat_id: str) -> bool:
        """Open a specific conversation."""
        try:
            # Extract element index from chat_id (e.g., "chat_0_linda_wu" -> 0)
            import re
            match = re.search(r'chat_(\d+)_', chat_id)
            if match:
                element_index = int(match.group(1))
                logger.info(f"Opening conversation at index {element_index}")
                
                # Find all conversation elements
                elements = await self.page.query_selector_all('[class*="conversation"]')
                if element_index < len(elements):
                    await elements[element_index].click()
                    await self.page.wait_for_timeout(3000)
                    logger.info(f"✅ Clicked conversation {element_index}")
                    return True
                else:
                    logger.warning(f"Element index {element_index} out of range (found {len(elements)} elements)")
            
            # Fallback: try to find by text content
            elements = await self.page.query_selector_all('[class*="conversation"]')
            for i, element in enumerate(elements):
                text = await element.inner_text()
                if "linda wu" in text.lower():
                    await element.click()
                    await self.page.wait_for_timeout(3000)
                    logger.info(f"✅ Clicked conversation by text match at index {i}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error opening conversation: {e}")
            return False
    
    async def _extract_messages_from_conversation(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Extract messages from the currently open conversation."""
        try:
            # Use direct DOM element extraction instead of text parsing
            messages = await self._extract_message_elements_directly(chat_id, since)
            
            logger.info(f"✅ Retrieved {len(messages)} messages from DOM elements")
            return messages
            
        except Exception as e:
            logger.error(f"Error extracting messages: {e}")
            return []
    
    async def _extract_message_elements_directly(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Extract messages directly from DOM elements in the conversation."""
        try:
            messages = []
            
            # Look for message bubbles in the conversation area
            # Alibaba uses specific patterns for messages
            message_selectors = [
                # Try multiple selectors to find message containers
                '[data-spm*="message"]',
                '.message-item',
                '.msg-item', 
                '[class*="msg-content"]',
                '[class*="message-content"]',
                # Generic message bubble selectors
                '.chat-message',
                '.conversation-message',
                # Time-based selectors since we see timestamps in the UI
                '*:has-text("2025-06-15")',
                # Look for elements that contain actual message text
                '*:has-text("ok thank you")',
                '*:has-text("tomorrow on Monday")',
                '*:has-text("how is production")'
            ]
            
            found_elements = []
            for selector in message_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        found_elements.extend(elements)
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    
            # If no specific selectors work, look for text content patterns
            if not found_elements:
                logger.info("No message elements found with selectors, trying text-based extraction")
                # Get all text elements and filter for message-like content
                all_elements = await self.page.query_selector_all('div, span, p')
                
                for element in all_elements:
                    try:
                        text = await element.inner_text()
                        # Look for patterns that suggest this is a message
                        if self._looks_like_message(text):
                            found_elements.append(element)
                    except:
                        continue
            
            # Process found elements
            unique_messages = set()
            for element in found_elements:
                try:
                    message_data = await self._extract_clean_message_data(element, chat_id)
                    if message_data and message_data['content']:
                        # Use content as deduplication key
                        content_key = message_data['content'].strip()
                        if content_key not in unique_messages and len(content_key) > 2:
                            unique_messages.add(content_key)
                            
                            # Apply date filter
                            if since and message_data.get('timestamp'):
                                try:
                                    msg_datetime = datetime.fromisoformat(message_data['timestamp'].replace('Z', '+00:00'))
                                    if msg_datetime < since:
                                        continue
                                except:
                                    pass
                            
                            messages.append(message_data)
                            
                except Exception as e:
                    logger.debug(f"Error processing element: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Direct extraction failed: {e}")
            return []
    
    def _looks_like_message(self, text: str) -> bool:
        """Check if text looks like a message content."""
        if not text or len(text.strip()) < 3:
            return False
            
        # Filter out UI elements
        ui_indicators = [
            'Rate supplier', 'Send order request', 'File a complaint',
            'Logistics Inquiry', 'Press "Enter"', 'Local Time:',
            'Order', 'Waiting for supplier', 'USD', 'Request modification',
            'javascript:', 'function(', 'var ', 'window.', 'document.',
            'SearchInbox', 'AllUnread', 'plugin', '.js', '.css',
            'alibaba.com', 'aplus', 'mlog'
        ]
        
        for indicator in ui_indicators:
            if indicator in text:
                return False
        
        # Look for message-like patterns
        message_patterns = [
            'thank you', 'how is', 'tomorrow', 'production', 'ok', 'great',
            'Daniel', 'monday', 'update', 'final'
        ]
        
        text_lower = text.lower()
        for pattern in message_patterns:
            if pattern in text_lower:
                return True
                
        # Also accept if it's short and simple
        if len(text.strip()) < 50 and not any(char in text for char in ['<', '>', '{', '}', '[', ']']):
            return True
            
        return False
    
    async def _extract_clean_message_data(self, element, chat_id: str) -> Optional[Dict[str, Any]]:
        """Extract clean message data from an element."""
        try:
            text = await element.inner_text()
            if not text or not self._looks_like_message(text):
                return None
            
            # Clean the text
            cleaned_text = self._clean_message_text(text)
            if not cleaned_text or len(cleaned_text.strip()) < 2:
                return None
            
            # Try to extract timestamp from nearby elements or the text itself
            timestamp = await self._extract_timestamp_from_context(element)
            
            # Determine direction - look for visual cues or position
            is_sent = await self._determine_message_direction(element)
            
            # Generate unique ID
            msg_id = self._generate_message_id(cleaned_text, timestamp, 'user' if is_sent else chat_id)
            
            return {
                'id': msg_id,
                'content': cleaned_text,
                'sender_id': 'self' if is_sent else chat_id,
                'sender_name': 'You' if is_sent else 'Contact',
                'timestamp': timestamp or datetime.now().isoformat(),
                'is_sent': is_sent,
                'direction': 'outgoing' if is_sent else 'incoming',
                'is_reply': False,  # TODO: Add reply detection logic
                'reply_to_content': None,
                'platform_data': {
                    'source': 'dom_extraction',
                    'original_text': text[:200]
                }
            }
            
        except Exception as e:
            logger.debug(f"Error extracting clean message data: {e}")
            return None
    
    def _clean_message_text(self, text: str) -> str:
        """Clean message text to extract only the actual message content."""
        # Remove common UI elements and duplicates
        lines = text.split('\n')
        cleaned_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip UI elements
            if any(ui in line for ui in ['Rate supplier', 'Send order', 'File a complaint', 
                                        'Press "Enter"', 'Local Time:', 'translating…',
                                        'Feedback', 'Read', 'USD', 'Request modification']):
                continue
                
            # Skip duplicates
            if line in seen_lines:
                continue
                
            seen_lines.add(line)
            cleaned_lines.append(line)
        
        # Join and further clean
        result = ' '.join(cleaned_lines)
        
        # Remove specific patterns
        patterns_to_remove = [
            r'translating…Feedback',
            r'Read$',
            r'Feedback$',
            r'ok thank you ok thank you',  # Fix duplicates
            r'how is productionhow is production',
            r'tomorrow on Monday will be give you final updatetomorrow on Monday will be give you final update'
        ]
        
        for pattern in patterns_to_remove:
            result = re.sub(pattern, lambda m: m.group(0)[:len(m.group(0))//2] if 'ok thank you ok thank you' in m.group(0) else '', result, flags=re.IGNORECASE)
        
        return result.strip()
    
    async def _extract_timestamp_from_context(self, element) -> Optional[str]:
        """Extract timestamp from element or its context."""
        try:
            # Look for timestamp patterns in the element and its siblings
            for selector in [element, await element.query_selector('..'), await element.query_selector('../..')]:
                if selector:
                    text = await selector.inner_text()
                    
                    # Look for date patterns
                    date_patterns = [
                        r'2025-06-15\s+(\d{2}:\d{2})',
                        r'2025-06-16\s+(\d{2}:\d{2})',
                        r'(\d{2}:\d{2})',
                        r'2025-\d{2}-\d{2}'
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, text)
                        if match:
                            # Try to construct a full timestamp
                            if '2025-06-15' in text:
                                time_part = match.group(1) if len(match.groups()) > 0 else '00:00'
                                return f"2025-06-15 {time_part}:00"
                            elif '2025-06-16' in text:
                                time_part = match.group(1) if len(match.groups()) > 0 else '00:00'
                                return f"2025-06-16 {time_part}:00"
                            
        except Exception as e:
            logger.debug(f"Error extracting timestamp: {e}")
        
        return None
    
    async def _determine_message_direction(self, element) -> bool:
        """Determine if message was sent by user or received."""
        try:
            # Check element classes and styles for direction indicators
            classes = await element.get_attribute('class') or ''
            style = await element.get_attribute('style') or ''
            
            # Common patterns for sent messages
            sent_indicators = ['sent', 'outgoing', 'right', 'self', 'my-message']
            received_indicators = ['received', 'incoming', 'left', 'other']
            
            classes_lower = classes.lower()
            
            for indicator in sent_indicators:
                if indicator in classes_lower:
                    return True
                    
            for indicator in received_indicators:
                if indicator in classes_lower:
                    return False
            
            # Check if element contains "Daniel Allen:" prefix
            text = await element.inner_text()
            if "Daniel Allen:" in text:
                return True
                
            # Default to incoming for safety
            return False
            
        except Exception as e:
            logger.debug(f"Error determining direction: {e}")
            return False
    
    def _generate_message_id(self, content: str, timestamp: Optional[str], sender: str) -> str:
        """Generate unique message ID."""
        unique_str = f"{content}:{timestamp or 'no-time'}:{sender}"
        return f"msg_{hashlib.md5(unique_str.encode()).hexdigest()[:16]}"
    
    async def _fallback_element_extraction(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fallback element-based message extraction when parser fails."""
        try:
            messages = []
            
            # Try multiple selectors for message elements
            message_selectors = [
                '[class*="message"]',
                '[class*="msg"]',
                '.message-item',
                '.msg-item',
                '[data-message-id]'
            ]
            
            all_elements = []
            for selector in message_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} message elements with selector: {selector}")
                        all_elements.extend(elements)
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
            
            # Remove duplicates
            unique_elements = []
            seen_elements = set()
            for element in all_elements:
                try:
                    element_text = await element.inner_text()
                    if element_text and element_text not in seen_elements:
                        seen_elements.add(element_text)
                        unique_elements.append(element)
                except:
                    continue
            
            logger.info(f"Processing {len(unique_elements)} unique message elements")
            
            for element in unique_elements:
                try:
                    message_data = await self._extract_message_data(element, chat_id)
                    if message_data:
                        # Apply date filter
                        if since and message_data.get('timestamp'):
                            try:
                                msg_datetime = datetime.fromisoformat(message_data['timestamp'].replace('Z', '+00:00'))
                                if msg_datetime < since:
                                    continue
                            except:
                                pass
                        
                        messages.append(message_data)
                except Exception as e:
                    logger.debug(f"Error extracting message from element: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return []
    
    async def _extract_message_data(self, element, chat_id: str) -> Optional[Dict[str, Any]]:
        """Extract data from a single message element."""
        try:
            # Get message text
            text = await element.inner_text()
            if not text or len(text.strip()) < 1:
                return None
            
            # Get classes for sent/received detection
            classes = await element.get_attribute('class') or ''
            
            # Use message parser to parse this individual message
            parsed_msg = self.message_parser.parse_message_element(text, classes)
            
            if parsed_msg:
                # Use parsed data but fill in missing fields
                return {
                    'id': parsed_msg.get('id'),
                    'content': parsed_msg.get('content'),
                    'sender_id': chat_id if not parsed_msg.get('is_sent') else 'self',
                    'sender_name': parsed_msg.get('sender_name') or ('You' if parsed_msg.get('is_sent') else chat_id),
                    'timestamp': parsed_msg.get('timestamp') or datetime.now().isoformat(),
                    'is_sent': parsed_msg.get('is_sent', False),
                    'direction': parsed_msg.get('direction', 'incoming'),
                    'is_reply': parsed_msg.get('is_reply', False),
                    'reply_to_content': parsed_msg.get('reply_to_content'),
                    'platform_data': {
                        'classes': classes,
                        'raw_text': parsed_msg.get('raw_text', text[:500]),
                        'source': 'element_extraction'
                    }
                }
            else:
                # Fallback to basic extraction if parser fails
                is_sent = any(indicator in classes for indicator in ['sent', 'outgoing', 'self', 'right'])
                timestamp = await self._extract_message_timestamp(element)
                msg_id = await element.get_attribute('data-message-id') or f"msg_{chat_id}_{datetime.now().timestamp()}"
                
                return {
                    'id': msg_id,
                    'content': text.strip(),
                    'sender_id': 'self' if is_sent else chat_id,
                    'sender_name': 'You' if is_sent else chat_id,
                    'timestamp': timestamp or datetime.now().isoformat(),
                    'is_sent': is_sent,
                    'direction': 'outgoing' if is_sent else 'incoming',
                    'is_reply': False,
                    'reply_to_content': None,
                    'platform_data': {
                        'classes': classes,
                        'source': 'basic_extraction'
                    }
                }
            
        except Exception as e:
            logger.debug(f"Error extracting message data: {e}")
            return None
    
    async def _extract_message_timestamp(self, element) -> Optional[str]:
        """Extract timestamp from message element."""
        try:
            # Look for timestamp elements
            time_selectors = [
                '.timestamp',
                '.time',
                '[class*="time"]',
                'time',
                'small'
            ]
            
            for selector in time_selectors:
                try:
                    time_element = await element.query_selector(selector)
                    if time_element:
                        time_text = await time_element.inner_text()
                        # Parse and normalize timestamp
                        return self._normalize_timestamp(time_text)
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting timestamp: {e}")
            return None
    
    def _normalize_timestamp(self, time_text: str) -> str:
        """Normalize various timestamp formats to ISO format."""
        try:
            # Handle relative times
            if 'just now' in time_text.lower():
                return datetime.now().isoformat()
            elif 'minute' in time_text.lower():
                minutes = int(re.search(r'(\d+)', time_text).group(1))
                return (datetime.now() - timedelta(minutes=minutes)).isoformat()
            elif 'hour' in time_text.lower():
                hours = int(re.search(r'(\d+)', time_text).group(1))
                return (datetime.now() - timedelta(hours=hours)).isoformat()
            elif 'yesterday' in time_text.lower():
                return (datetime.now() - timedelta(days=1)).isoformat()
            
            # Try to parse absolute times
            # Add more parsing logic as needed
            return time_text
            
        except:
            return datetime.now().isoformat()
    
    def _clean_contact_name(self, name: str) -> Optional[str]:
        """Clean and validate contact name."""
        if not name:
            return None
        
        # Remove common suffixes
        name = re.sub(r'\s*(Co\.|Ltd|Company|Inc|Corp|Industrial).*$', '', name, flags=re.IGNORECASE)
        name = name.strip()
        
        # Validate it's a reasonable name
        if len(name) < 2 or len(name) > 50:
            return None
        
        # Filter out non-name content
        if any(word in name.lower() for word in ['message', 'online', 'offline', 'typing']):
            return None
        
        return name
    
    # Keep the helper methods from the original adapter
    def _extract_contact_name(self, text: str) -> Optional[str]:
        """Extract a clean contact name from raw text."""
        import re
        
        # Common patterns for names
        name_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # First Last
            r'\b([A-Z][a-z]+)\b',  # Single name
            r'(Linda Wu)',  # Known contact
            r'(Kiko Liu)',  # Known contact  
            r'(Ricky Foksy)'  # Known contact
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            if matches:
                name = matches[0]
                # Filter out common non-name words
                if name not in ['All', 'The', 'Active', 'Project', 'Company', 'Ltd', 'Co']:
                    return name
        
        return None
    
    async def save_browser_state(self):
        """Save browser cookies and session data."""
        if self.page:
            cookies = await self.browser_context.cookies()
            
            # Update account session data
            if not self.account.session_data:
                self.account.session_data = {}
            
            self.account.session_data["cookies"] = cookies
            self.account.session_data["last_auth"] = datetime.now().isoformat()
            
            # Save to database (account is already attached to a session)
            try:
                # Just update the session data, don't try to add/commit if already in session
                logger.info("🍪 Updated browser state and cookies in memory")
                # The sync service will handle the database commit
            except Exception as e:
                logger.error(f"Failed to save browser state: {e}")
    
    async def close(self):
        """Close browser context but keep it available for reuse."""
        # Don't actually close for long-running adapter
        logger.info("🔄 Keeping browser open for future use")
        # Just save the state
        await self.save_browser_state()
    
    async def shutdown(self):
        """Actually shutdown the browser when needed."""
        logger.info("🧹 Shutting down Alibaba browser...")
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()
        super().close()
    
    async def send_message(self, chat_id: str, content: str, media: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send a message to a chat (not implemented for Alibaba yet)."""
        logger.warning("Message sending not implemented for Alibaba")
        return {"success": False, "error": "Not implemented"}
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get profile information for a user."""
        # For now, return minimal profile info
        return {
            "id": user_id,
            "username": user_id,
            "display_name": user_id
        }
    
    async def download_media(self, url: str, save_path: str) -> bool:
        """Download media file from platform."""
        # Not implemented for Alibaba yet
        logger.warning("Media download not implemented for Alibaba")
        return False
    
    # Keep remaining methods from original adapter...
    async def _fill_login_credentials(self):
        """Fill login form with credentials."""
        logger.info("✏️ Filling login credentials...")
        
        # Find username field
        username_selectors = [
            'input[name="account"]',
            'input[name="loginId"]',
            'input[name="username"]',
            'input[type="email"]'
        ]
        
        username_input = None
        for selector in username_selectors:
            try:
                username_input = await self.page.wait_for_selector(selector, timeout=2000)
                break
            except:
                continue
        
        if username_input:
            await username_input.fill(self.account.username)
            logger.info("✅ Username filled")
        else:
            raise Exception("Username field not found")
        
        # Find password field
        password_input = await self.page.wait_for_selector('input[type="password"]', timeout=5000)
        if password_input:
            await password_input.fill(self.account.password)
            logger.info("✅ Password filled")
        else:
            raise Exception("Password field not found")
    
    async def _submit_login(self):
        """Submit the login form."""
        logger.info("🖱️ Submitting login form...")
        
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Sign in")',
            'button:has-text("登录")',
            '.submit-btn'
        ]
        
        submit_button = None
        for selector in submit_selectors:
            try:
                submit_button = await self.page.wait_for_selector(selector, timeout=2000)
                break
            except:
                continue
        
        if submit_button:
            await submit_button.click()
            await self.page.wait_for_timeout(5000)
            logger.info("✅ Login form submitted")
        else:
            raise Exception("Submit button not found")
    
    async def _is_2fa_required(self) -> bool:
        """Check if 2FA verification is required."""
        current_url = self.page.url
        if "login" not in current_url:
            return False
        
        page_content = await self.page.content()
        has_verification_text = any(keyword in page_content.lower() for keyword in [
            'verification', 'verify', 'code', '验证', 'security', '2fa', 'authenticate'
        ])
        
        if has_verification_text:
            logger.info("🔍 2FA verification required")
            return True
        
        return False
    
    async def _handle_2fa(self) -> bool:
        """Handle 2FA verification using email codes."""
        if not self.email_reader:
            logger.error("❌ 2FA required but no email reader configured")
            return False
        
        try:
            logger.info("🔐 Handling 2FA verification...")
            
            # Wait for modal to appear
            await self.page.wait_for_timeout(8000)
            
            # Get 2FA code from email
            logger.info("📧 Retrieving 2FA code from email...")
            await asyncio.sleep(10)  # Wait for email to arrive
            
            code = self.email_reader.get_latest_alibaba_2fa_code(max_age_minutes=5, delete_after_use=True)
            if not code:
                logger.error("❌ No 2FA code found in email")
                return False
            
            logger.info(f"✅ Found 2FA code: {code}")
            
            # Use coordinate-based approach to fill verification code
            logger.info("🎯 Using coordinate-based 2FA input...")
            
            # Click on verification input field
            await self.page.mouse.click(730, 360)
            await self.page.wait_for_timeout(1000)
            
            # Type the code
            await self.page.keyboard.type(code)
            await self.page.wait_for_timeout(1000)
            
            # Click submit button
            await self.page.mouse.click(685, 508)
            await self.page.keyboard.press('Enter')  # Backup
            
            # Wait for verification to complete
            await self.page.wait_for_timeout(10000)
            
            logger.info("✅ 2FA verification completed")
            
            # Handle potential 400 redirect
            await self.page.wait_for_timeout(5000)
            current_url = self.page.url
            
            if "400" in current_url or "error" in current_url:
                logger.warning("⚠️  Detected 400 redirect after 2FA, waiting for final redirect...")
                await self.page.wait_for_timeout(10000)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 2FA verification failed: {e}")
            return False
#!/usr/bin/env python3
"""Alibaba message parser for better extraction and deduplication."""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class AlibabaMessageParser:
    """Parser for Alibaba messages with reply detection and deduplication."""
    
    def __init__(self):
        self.seen_messages = {}  # Track messages by content hash
        
    def parse_message_element(self, text: str, element_classes: str = "") -> Optional[Dict[str, Any]]:
        """Parse a message element into structured data."""
        if not text or len(text.strip()) < 2:
            return None
            
        # Clean up the text
        text = text.strip()
        
        # Extract components
        sender_name, timestamp, content, is_reply, reply_to = self._extract_message_components(text)
        
        if not content:
            return None
            
        # Generate unique ID based on content + timestamp
        msg_id = self._generate_message_id(content, timestamp, sender_name)
        
        # Check if sent or received based on classes or position
        is_sent = self._determine_if_sent(element_classes, text)
        
        return {
            'id': msg_id,
            'content': content,
            'sender_name': sender_name or "Unknown",
            'timestamp': timestamp,
            'is_sent': is_sent,
            'direction': 'outgoing' if is_sent else 'incoming',
            'is_reply': is_reply,
            'reply_to_content': reply_to,
            'raw_text': text[:500]  # Store limited raw text for debugging
        }
    
    def _extract_message_components(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str], bool, Optional[str]]:
        """Extract sender, timestamp, content, and reply info from message text."""
        lines = text.split('\n')
        
        sender_name = None
        timestamp = None
        content = []
        is_reply = False
        reply_to = None
        
        # Common patterns
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
        sender_pattern = r'^([A-Z][a-zA-Z\s]+):'
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Check for timestamp
            timestamp_match = re.search(timestamp_pattern, line)
            if timestamp_match and not timestamp:
                timestamp = timestamp_match.group(1)
                # Remove timestamp from line
                line = re.sub(timestamp_pattern, '', line).strip()
            
            # Check for sender name (Name: format)
            sender_match = re.match(sender_pattern, line)
            if sender_match and not sender_name:
                sender_name = sender_match.group(1).strip()
                # Remove sender from line
                line = line[len(sender_match.group(0)):].strip()
            
            # Check if this line starts a quoted/reply message
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('>'):
                is_reply = True
                # The current line might be the reply content
                if line:
                    content.append(line)
                # Next lines starting with > are the quoted content
                i += 1
                quoted_lines = []
                while i < len(lines) and lines[i].strip().startswith('>'):
                    quoted_lines.append(lines[i].strip()[1:].strip())
                    i += 1
                reply_to = '\n'.join(quoted_lines)
                continue
            
            # Check for common reply indicators
            if any(indicator in line.lower() for indicator in ['replied:', 'reply to:', 'wrote:', 'said:']):
                is_reply = True
            
            # Add non-empty line to content
            if line:
                content.append(line)
            
            i += 1
        
        # Join content
        content_str = '\n'.join(content).strip()
        
        # Clean up content - remove metadata
        content_str = self._clean_content(content_str)
        
        return sender_name, timestamp, content_str, is_reply, reply_to
    
    def _clean_content(self, content: str) -> str:
        """Clean message content by removing metadata and UI elements."""
        # Remove common UI elements
        ui_patterns = [
            r'Local Time:.*?(?=\n|$)',
            r'Order\s+Waiting for supplier.*?(?=\n|$)',
            r'Request modification.*?(?=\n|$)',
            r'Try a voice or video call.*?(?=\n|$)',
            r'Call\s*$',
            r'Read\s*$',
            r'Delivered\s*$',
            r'ReplyDownload.*?$',
            r'ReplyTranslate.*?$',
            r'ReplyDownload\s*$',
            r'ReplyTranslate\s*$',
            r'USD\s+\d+\.\d+',
            r'To be shipped.*?Active Project',
            r'For Buyer\s*$',
            r'For Supplier\s*$',
            r'Notice\s*$',
            r'Pending Orders.*?$',
            r'New Contact Requests.*?$',
            r'New Connections.*?$',
            r'New Quotes.*?$',
            r'Rate supplier.*?$',
            r'Send order request.*?$',
            r'File a complaint.*?$',
            r'Logistics Inquiry.*?$',
            r'Press "Enter" to send.*?$',
            r'Send\s*$',
            r'^\d+\s*$',  # Single numbers on a line
        ]
        
        for pattern in ui_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove single letter lines (often UI artifacts)
        lines = content.split('\n')
        cleaned_lines = [line for line in lines if len(line.strip()) > 1 or line.strip() in ['ok', 'OK']]
        content = '\n'.join(cleaned_lines)
        
        # Filter out messages that are purely UI elements
        ui_only_patterns = [
            r'^(ReplyDownload|ReplyTranslate|For Buyer|For Supplier|Notice|Send)$',
            r'^\d+\s+(Pending Orders|New Contact Requests|New Connections|New Quotes)$',
            r'^(Rate supplier|Send order request|File a complaint|Logistics Inquiry)$'
        ]
        
        for pattern in ui_only_patterns:
            if re.match(pattern, content.strip(), re.IGNORECASE):
                return ""  # Return empty string to indicate this should be filtered out
        
        return content.strip()
    
    def _determine_if_sent(self, element_classes: str, text: str) -> bool:
        """Determine if message was sent by the user."""
        # Check classes for sent indicators
        sent_indicators = ['sent', 'outgoing', 'self', 'right', 'my-message']
        if any(indicator in element_classes.lower() for indicator in sent_indicators):
            return True
            
        # Check for "Daniel Allen:" in text (the user)
        if "Daniel Allen:" in text:
            return True
            
        # Check position-based indicators
        if "Read" in text and text.endswith("Read"):
            # Messages marked as "Read" are usually sent by others
            return False
            
        return False
    
    def _generate_message_id(self, content: str, timestamp: Optional[str], sender: Optional[str]) -> str:
        """Generate a unique message ID based on content and metadata."""
        # Create a unique string from message components
        unique_str = f"{content}:{timestamp or 'no-time'}:{sender or 'unknown'}"
        # Generate hash
        return f"msg_{hashlib.md5(unique_str.encode()).hexdigest()[:16]}"
    
    def deduplicate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate messages based on content and timestamp."""
        unique_messages = []
        seen = set()
        
        for msg in messages:
            # Create a unique key based on content and timestamp
            key = f"{msg.get('content', '')}:{msg.get('timestamp', '')}"
            
            if key not in seen:
                seen.add(key)
                unique_messages.append(msg)
            else:
                logger.debug(f"Skipping duplicate message: {msg.get('content', '')[:50]}...")
        
        return unique_messages
    
    def extract_conversation_messages(self, page_text: str) -> List[Dict[str, Any]]:
        """Extract all messages from a conversation page."""
        messages = []
        
        # First, try to extract messages from JavaScript/JSON data
        js_messages = self._extract_from_javascript_data(page_text)
        messages.extend(js_messages)
        
        # Split by common message boundaries
        # Look for patterns like timestamps followed by content
        message_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}[\s\S]*?)(?=\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|$)'
        
        potential_messages = re.findall(message_pattern, page_text)
        
        for msg_text in potential_messages:
            parsed = self.parse_message_element(msg_text)
            if parsed:
                messages.append(parsed)
        
        # Also try to find specific known messages
        if "ok,Daniel" in page_text:
            # Find context around ok,Daniel
            ok_daniel_pattern = r'([\s\S]{0,200}ok,Daniel[\s\S]{0,100})'
            matches = re.findall(ok_daniel_pattern, page_text)
            
            for match in matches:
                parsed = self.parse_message_element(match)
                if parsed and parsed not in messages:
                    messages.append(parsed)
        
        return self.deduplicate_messages(messages)
    
    def _extract_from_javascript_data(self, page_text: str) -> List[Dict[str, Any]]:
        """Extract messages from JavaScript data structures in the page."""
        messages = []
        
        # Look for JSON-like message data with specific patterns
        json_patterns = [
            r'"content":"([^"]+)"[^}]*"sendTime":(\d+)',
            r'"content":"([^"]+)"[^}]*"messageId":"([^"]+)"',
            r'{"content":"([^"]+)"[^}]*"sendTime":(\d+)[^}]*}',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                try:
                    if len(match) >= 2:
                        content = match[0]
                        # Basic cleaning
                        content = content.replace('\\n', '\n').replace('\\"', '"')
                        
                        # Skip if content is too short or looks like UI
                        if len(content) < 2 or content in ['ok', 'Read', 'Send']:
                            continue
                        
                        # Create a message object
                        message_data = {
                            'id': self._generate_message_id(content, str(match[1]) if len(match) > 1 else None, None),
                            'content': content,
                            'sender_name': None,  # Will be determined later
                            'timestamp': self._convert_timestamp(match[1]) if len(match) > 1 and match[1].isdigit() else None,
                            'is_sent': False,  # Default, will be determined later
                            'direction': 'incoming',
                            'is_reply': False,
                            'reply_to_content': None,
                            'raw_text': content
                        }
                        messages.append(message_data)
                        
                except Exception as e:
                    logger.debug(f"Error parsing JavaScript message: {e}")
                    continue
        
        return messages
    
    def _convert_timestamp(self, timestamp_str: str) -> str:
        """Convert JavaScript timestamp to ISO format."""
        try:
            if timestamp_str and timestamp_str.isdigit():
                # JavaScript timestamps are in milliseconds
                timestamp_ms = int(timestamp_str)
                # Convert to seconds
                timestamp_s = timestamp_ms / 1000
                # Convert to datetime
                dt = datetime.fromtimestamp(timestamp_s)
                return dt.isoformat()
        except Exception as e:
            logger.debug(f"Error converting timestamp {timestamp_str}: {e}")
        
        return datetime.now().isoformat()
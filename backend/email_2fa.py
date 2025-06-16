#!/usr/bin/env python3
"""IMAP email reader for 2FA codes."""
import imaplib
import email
import re
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class EmailTwoFactorReader:
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.fastmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.mail = None
        
    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            logger.info(f"Connecting to IMAP server: {self.imap_server}")
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            logger.info("✅ IMAP connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ IMAP connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
                
    def get_latest_alibaba_2fa_code(self, max_age_minutes: int = 5, delete_after_use: bool = True) -> Optional[str]:
        """
        Get the latest 2FA code from Alibaba emails and optionally delete the email.
        
        Args:
            max_age_minutes: Only look for emails newer than this many minutes
            delete_after_use: Whether to delete the email after extracting the code
            
        Returns:
            2FA code if found, None otherwise
        """
        try:
            if not self.connect():
                return None
                
            # Select inbox
            self.mail.select('INBOX')
            
            # Search for recent emails from Alibaba
            since_date = (datetime.now() - timedelta(minutes=max_age_minutes)).strftime("%d-%b-%Y")
            
            # Search criteria for Alibaba 2FA emails
            search_criteria = [
                f'(SINCE "{since_date}" FROM "alibaba")',
                f'(SINCE "{since_date}" FROM "noreply")',
                f'(SINCE "{since_date}" SUBJECT "verification")',
                f'(SINCE "{since_date}" SUBJECT "code")',
                f'(SINCE "{since_date}" SUBJECT "security")',
            ]
            
            for criteria in search_criteria:
                logger.info(f"Searching with criteria: {criteria}")
                typ, data = self.mail.search(None, criteria)
                
                if typ == 'OK' and data[0]:
                    email_ids = data[0].split()
                    logger.info(f"Found {len(email_ids)} emails matching criteria")
                    
                    # Check emails from newest to oldest
                    for email_id in reversed(email_ids):
                        code = self._extract_code_from_email(email_id)
                        if code:
                            logger.info(f"✅ Found 2FA code: {code}")
                            
                            # Delete the email after successful code extraction
                            if delete_after_use:
                                try:
                                    self.mail.store(email_id, '+FLAGS', '\\Deleted')
                                    self.mail.expunge()
                                    logger.info(f"🗑️  Deleted used 2FA email {email_id.decode()}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete email {email_id.decode()}: {e}")
                            
                            return code
                            
            logger.warning("No 2FA code found in recent emails")
            return None
            
        except Exception as e:
            logger.error(f"Error reading emails: {e}")
            return None
        finally:
            self.disconnect()
    
    def _extract_code_from_email(self, email_id: bytes) -> Optional[str]:
        """Extract 2FA code from a specific email."""
        try:
            # Fetch the email
            typ, data = self.mail.fetch(email_id, '(RFC822)')
            if typ != 'OK':
                return None
                
            # Parse the email
            email_message = email.message_from_bytes(data[0][1])
            
            # Get email details
            sender = email_message.get('From', '')
            subject = email_message.get('Subject', '')
            date_str = email_message.get('Date', '')
            
            logger.info(f"Checking email from: {sender}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Date: {date_str}")
            
            # Check if this looks like an Alibaba email
            if not any(keyword in sender.lower() for keyword in ['alibaba', 'noreply']) and \
               not any(keyword in subject.lower() for keyword in ['verification', 'code', 'security', 'login']):
                return None
            
            # Extract text content
            email_body = self._get_email_body(email_message)
            if not email_body:
                return None
                
            logger.info(f"Email body preview: {email_body[:200]}...")
            
            # Look for verification codes - common patterns
            code_patterns = [
                r'verification code[:\s]+(\d{4,8})',
                r'security code[:\s]+(\d{4,8})',
                r'code[:\s]+(\d{4,8})',
                r'(\d{6})',  # 6-digit code
                r'(\d{4})',  # 4-digit code
                r'(\d{8})',  # 8-digit code
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, email_body, re.IGNORECASE)
                if matches:
                    # Return the first numeric code found
                    for match in matches:
                        if match.isdigit() and 4 <= len(match) <= 8:
                            logger.info(f"Found potential 2FA code: {match}")
                            return match
                            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting code from email: {e}")
            return None
    
    def _get_email_body(self, email_message) -> str:
        """Extract text body from email message."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                    
                if content_type == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        part_body = part.get_payload(decode=True).decode(charset)
                        body += part_body
                    except:
                        continue
                elif content_type == "text/html" and not body:
                    # Use HTML as fallback if no plain text
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        part_body = part.get_payload(decode=True).decode(charset)
                        # Simple HTML tag removal
                        import re
                        part_body = re.sub('<[^<]+?>', '', part_body)
                        body += part_body
                    except:
                        continue
        else:
            charset = email_message.get_content_charset() or 'utf-8'
            try:
                body = email_message.get_payload(decode=True).decode(charset)
            except:
                body = str(email_message.get_payload())
                
        return body.strip()

def test_email_reader():
    """Test the email reader functionality."""
    # Use your credentials
    reader = EmailTwoFactorReader(
        email_address="daniel_allen@fastmail.com",
        password="YOUR_EMAIL_PASSWORD_HERE"  # You'll need to provide this
    )
    
    print("Testing email 2FA reader...")
    code = reader.get_latest_alibaba_2fa_code(max_age_minutes=10)
    
    if code:
        print(f"✅ Found 2FA code: {code}")
    else:
        print("❌ No 2FA code found")

if __name__ == "__main__":
    test_email_reader()
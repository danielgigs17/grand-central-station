#!/usr/bin/env python3
"""
Manual testing script for Alibaba adapter implementation.
This script helps coordinate manual testing with the adapter development.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.alibaba_real import AlibabaRealAdapter, AlibabaRealBrowserAdapter
from app.models.platform_account import PlatformAccount
from app.core.config import settings
import json
from datetime import datetime


class AlibabaManualTester:
    def __init__(self):
        self.adapter = None
        self.use_browser = False
        
    async def setup(self):
        """Setup the adapter with credentials."""
        print("\n=== ALIBABA ADAPTER MANUAL TESTING ===")
        print("\nThis script will help test the Alibaba adapter implementation.")
        print("Make sure you have set ALIBABA_USERNAME and ALIBABA_PASSWORD in your .env file")
        
        # Check for credentials
        if not settings.ALIBABA_USERNAME or not settings.ALIBABA_PASSWORD:
            print("\n❌ ERROR: Missing credentials!")
            print("Please set ALIBABA_USERNAME and ALIBABA_PASSWORD in your .env file")
            return False
            
        # Ask which adapter to use
        choice = input("\nWhich adapter to test? (1) HTTP API (2) Browser Automation: ")
        self.use_browser = choice == "2"
        
        # Create account object
        account = PlatformAccount(
            username=settings.ALIBABA_USERNAME,
            password=settings.ALIBABA_PASSWORD,
            platform_name="alibaba"
        )
        
        # Initialize adapter
        if self.use_browser:
            self.adapter = AlibabaRealBrowserAdapter(account)
            print("\n✅ Using Browser Automation Adapter")
        else:
            self.adapter = AlibabaRealAdapter(account)
            print("\n✅ Using HTTP API Adapter")
            
        return True
        
    async def test_authentication(self):
        """Test the authentication flow."""
        print("\n--- Testing Authentication ---")
        print("Please monitor your browser DevTools Network tab...")
        input("Press Enter when ready to start login...")
        
        print("\n🔐 Attempting authentication...")
        success = await self.adapter.authenticate()
        
        if success:
            print("✅ Authentication successful!")
            print(f"User ID: {self.adapter.user_id}")
            print(f"CSRF Token: {self.adapter.csrf_token}")
        else:
            print("❌ Authentication failed!")
            print("\nPlease check:")
            print("1. Are credentials correct?")
            print("2. Any CAPTCHA present?")
            print("3. Check browser console for errors")
            
        return success
        
    async def test_get_chats(self):
        """Test retrieving conversation list."""
        print("\n--- Testing Get Chats ---")
        print("Attempting to retrieve conversation list...")
        
        try:
            chats = await self.adapter.get_chats()
            
            if chats:
                print(f"\n✅ Found {len(chats)} conversations!")
                for i, chat in enumerate(chats[:5]):  # Show first 5
                    print(f"\n{i+1}. {chat.get('title', 'Unknown')}")
                    print(f"   Last message: {chat.get('last_message', 'N/A')}")
                    print(f"   Unread: {chat.get('unread_count', 0)}")
                    
                # Save for reference
                with open("logs/chats_response.json", "w") as f:
                    json.dump(chats, f, indent=2)
                print("\n💾 Full response saved to logs/chats_response.json")
            else:
                print("❌ No chats found or request failed")
                
        except Exception as e:
            print(f"❌ Error getting chats: {e}")
            
        return len(chats) > 0 if chats else False
        
    async def test_get_messages(self):
        """Test retrieving messages for a chat."""
        print("\n--- Testing Get Messages ---")
        
        chat_id = input("Enter chat ID (or press Enter to skip): ").strip()
        if not chat_id:
            print("Skipping message retrieval test")
            return False
            
        try:
            messages = await self.adapter.get_messages(chat_id)
            
            if messages:
                print(f"\n✅ Found {len(messages)} messages!")
                for msg in messages[:5]:  # Show first 5
                    print(f"\n- {msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}")
                    print(f"  Time: {msg.get('timestamp', 'N/A')}")
            else:
                print("❌ No messages found or not implemented")
                
        except Exception as e:
            print(f"❌ Error getting messages: {e}")
            
        return False
        
    async def test_send_message(self):
        """Test sending a message."""
        print("\n--- Testing Send Message ---")
        
        chat_id = input("Enter chat ID to send message (or press Enter to skip): ").strip()
        if not chat_id:
            print("Skipping message send test")
            return False
            
        message = input("Enter message to send: ").strip()
        if not message:
            print("No message entered, skipping")
            return False
            
        print(f"\n📤 Sending message to chat {chat_id}...")
        print("Please monitor Network tab for the request...")
        
        try:
            result = await self.adapter.send_message(chat_id, message)
            
            if result:
                print("✅ Message sent successfully!")
                print(f"Result: {result}")
            else:
                print("❌ Failed to send message or not implemented")
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            
        return False
        
    async def interactive_testing(self):
        """Interactive testing menu."""
        while True:
            print("\n=== MANUAL TESTING MENU ===")
            print("1. Test Authentication")
            print("2. Test Get Chats")
            print("3. Test Get Messages")
            print("4. Test Send Message")
            print("5. Export HAR Analysis")
            print("0. Exit")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                await self.test_authentication()
            elif choice == "2":
                await self.test_get_chats()
            elif choice == "3":
                await self.test_get_messages()
            elif choice == "4":
                await self.test_send_message()
            elif choice == "5":
                self.export_har_instructions()
            else:
                print("Invalid option")
                
    def export_har_instructions(self):
        """Show instructions for exporting HAR file."""
        print("\n=== HAR FILE EXPORT INSTRUCTIONS ===")
        print("\n1. Open Chrome DevTools (F12)")
        print("2. Go to Network tab")
        print("3. Clear existing requests (🚫 button)")
        print("4. Check 'Preserve log' checkbox")
        print("5. Perform the action (login, get chats, etc.)")
        print("6. Right-click in Network tab → 'Save all as HAR with content'")
        print("7. Run: python tools/alibaba_har_analyzer.py <har_file>")
        print("\nThis will help identify the exact API endpoints and parameters.")


async def main():
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    tester = AlibabaManualTester()
    
    if not await tester.setup():
        return
        
    # Run interactive testing
    await tester.interactive_testing()
    
    print("\n✅ Testing complete!")
    print("Check logs/ directory for saved responses")


if __name__ == "__main__":
    asyncio.run(main())
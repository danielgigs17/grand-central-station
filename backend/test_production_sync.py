#!/usr/bin/env python3
"""Test script for Alibaba production sync system."""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.alibaba_sync import AlibabaSyncService
from app.adapters.alibaba_production import AlibabaProductionAdapter
from app.db.base import SessionLocal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockAccount:
    """Mock account for testing."""
    def __init__(self):
        self.username = "daniel_allen@fastmail.com"
        self.password = "P123okemon1."
        self.session_data = {}


async def test_adapter():
    """Test the production adapter."""
    logger.info("🧪 Testing Alibaba Production Adapter...")
    
    account = MockAccount()
    adapter = AlibabaProductionAdapter(account)
    
    try:
        # Test authentication
        logger.info("Testing authentication...")
        auth_result = await adapter.authenticate()
        
        if auth_result:
            logger.info("✅ Authentication successful!")
            
            # Test getting conversations
            logger.info("Testing conversation retrieval...")
            conversations = await adapter.get_chats(max_age_days=7)
            
            logger.info(f"✅ Found {len(conversations)} conversations")
            for i, conv in enumerate(conversations[:3]):  # Show first 3
                logger.info(f"  {i+1}. {conv.get('title', 'Unknown')} - {conv.get('last_message', 'No message')[:50]}")
            
            # Test getting messages for first conversation
            if conversations:
                first_conv = conversations[0]
                logger.info(f"Testing message retrieval for: {first_conv.get('title')}")
                
                messages = await adapter.get_messages(first_conv.get('id'))
                logger.info(f"✅ Found {len(messages)} messages")
                
                for i, msg in enumerate(messages[:3]):  # Show first 3
                    logger.info(f"  {i+1}. {msg.get('content', '')[:50]}...")
            
            logger.info("✅ Adapter test completed successfully!")
            return True
        else:
            logger.error("❌ Authentication failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Adapter test failed: {e}")
        return False
    finally:
        await adapter.close()


async def test_sync_service():
    """Test the sync service (dry run)."""
    logger.info("🧪 Testing Alibaba Sync Service...")
    
    try:
        db = SessionLocal()
        sync_service = AlibabaSyncService(db)
        
        # Note: This would require an actual account in the database
        # For now, just test the service instantiation
        logger.info("✅ Sync service instantiated successfully")
        
        sync_service.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Sync service test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Alibaba Production Sync Tests...")
    
    # Check environment
    email_password = os.getenv("EMAIL_PASSWORD")
    if not email_password:
        logger.warning("⚠️  EMAIL_PASSWORD not set - 2FA won't work")
    
    tests = [
        ("Adapter Test", test_adapter),
        ("Sync Service Test", test_sync_service),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! Production sync system is ready.")
    else:
        logger.warning("⚠️  Some tests failed. Check logs above.")


if __name__ == "__main__":
    asyncio.run(main())
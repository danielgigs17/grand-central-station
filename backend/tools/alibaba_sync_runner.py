#!/usr/bin/env python3
"""Standalone Alibaba sync runner that handles missing dependencies gracefully."""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockAccount:
    """Mock account for testing without database."""
    def __init__(self):
        self.username = os.getenv("ALIBABA_USERNAME", "daniel_allen@fastmail.com")
        self.password = os.getenv("ALIBABA_PASSWORD", "P123okemon1.")
        self.session_data = {}


async def run_adapter_test():
    """Test the Alibaba adapter."""
    try:
        from app.adapters.alibaba_production import AlibabaProductionAdapter
        
        account = MockAccount()
        adapter = AlibabaProductionAdapter(account)
        
        logger.info("🧪 Testing Alibaba Production Adapter...")
        
        # Test authentication
        if await adapter.authenticate():
            logger.info("✅ Authentication successful!")
            
            # Test getting conversations
            conversations = await adapter.get_chats(max_age_days=7)
            logger.info(f"📋 Found {len(conversations)} conversations")
            
            for i, conv in enumerate(conversations[:3]):
                logger.info(f"  {i+1}. {conv.get('title', 'Unknown')}: {conv.get('last_message', '')[:50]}")
            
            # Test getting messages
            if conversations:
                messages = await adapter.get_messages(conversations[0].get('id'))
                logger.info(f"📬 Found {len(messages)} messages in first conversation")
                
                for i, msg in enumerate(messages[:2]):
                    logger.info(f"  {i+1}. {msg.get('content', '')[:50]}...")
            
            logger.info("🎉 Adapter test completed successfully!")
            return True
        else:
            logger.error("❌ Authentication failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Adapter test failed: {e}")
        return False
    finally:
        await adapter.close()


async def run_periodic_sync(interval_minutes: int = 5):
    """Run periodic sync without database dependency."""
    logger.info(f"🔄 Starting periodic Alibaba sync (every {interval_minutes} minutes)")
    logger.info("⚠️  Note: Running without database - messages will not be stored")
    logger.info("📋 Press Ctrl+C to stop")
    
    try:
        from app.adapters.alibaba_production import AlibabaProductionAdapter
        
        # Perform initial sync
        await perform_sync_cycle("Initial")
        
        # Start periodic loop
        while True:
            await asyncio.sleep(interval_minutes * 60)
            await perform_sync_cycle("Incremental")
            
    except KeyboardInterrupt:
        logger.info("👋 Received interrupt, stopping...")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")


async def perform_sync_cycle(sync_type: str):
    """Perform a single sync cycle."""
    logger.info(f"🔄 Starting {sync_type} sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    account = MockAccount()
    adapter = None
    
    try:
        from app.adapters.alibaba_production import AlibabaProductionAdapter
        adapter = AlibabaProductionAdapter(account)
        
        # Authenticate
        if await adapter.authenticate():
            logger.info("✅ Authentication successful")
            
            # Get conversations
            conversations = await adapter.get_chats(max_age_days=7)
            logger.info(f"📋 Found {len(conversations)} conversations")
            
            # Show summary
            total_messages = 0
            for conv in conversations:
                messages = await adapter.get_messages(conv.get('id'))
                total_messages += len(messages)
                
                if "ok,Daniel" in str(messages):
                    logger.info("🎯 Found target message 'ok,Daniel'!")
            
            logger.info(f"📬 Total messages found: {total_messages}")
            logger.info(f"✅ {sync_type} sync completed successfully")
            
        else:
            logger.error(f"❌ {sync_type} sync failed: Authentication failed")
            
    except Exception as e:
        logger.error(f"❌ {sync_type} sync failed: {e}")
    finally:
        if adapter:
            await adapter.close()
        
        logger.info(f"⏰ Next sync in {5} minutes...")


async def run_database_sync(interval_minutes: int = 5):
    """Run full database sync (requires database setup)."""
    try:
        # Try to import database components
        from app.services.alibaba_scheduler import AlibabaSchedulerService
        
        logger.info(f"🚀 Starting full database sync scheduler (every {interval_minutes} minutes)")
        
        scheduler = AlibabaSchedulerService(sync_interval_minutes=interval_minutes)
        await scheduler.start()
        
    except ImportError as e:
        logger.error(f"❌ Database components not available: {e}")
        logger.info("💡 Try running: pip install sqlalchemy psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"❌ Database sync failed: {e}")
        return False


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alibaba Sync Runner")
    parser.add_argument("command", choices=["test", "sync", "database"], help="Command to run")
    parser.add_argument("--interval", type=int, default=5, help="Sync interval in minutes")
    
    args = parser.parse_args()
    
    # Check environment
    if not os.getenv("EMAIL_PASSWORD"):
        logger.error("❌ EMAIL_PASSWORD environment variable not set")
        return
    
    if args.command == "test":
        await run_adapter_test()
    elif args.command == "sync":
        await run_periodic_sync(args.interval)
    elif args.command == "database":
        await run_database_sync(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
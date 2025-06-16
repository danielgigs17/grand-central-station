#!/usr/bin/env python3
"""Alibaba message sync scheduler service."""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.alibaba_sync import AlibabaSyncService
from app.models import PlatformAccount, Platform
from app.db.base import SessionLocal

logger = logging.getLogger(__name__)


class AlibabaSchedulerService:
    """Service that manages periodic Alibaba message synchronization."""
    
    def __init__(self, sync_interval_minutes: int = 5):
        self.sync_interval_minutes = sync_interval_minutes
        self.running = False
        self.sync_task = None
        self.db = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    async def start(self):
        """Start the scheduler service."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info(f"🚀 Starting Alibaba scheduler (sync every {self.sync_interval_minutes} minutes)...")
        self.running = True
        
        # Perform initial sync for all Alibaba accounts
        await self._perform_initial_sync()
        
        # Start periodic sync loop
        self.sync_task = asyncio.create_task(self._sync_loop())
        
        try:
            await self.sync_task
        except asyncio.CancelledError:
            logger.info("Scheduler task cancelled")
        finally:
            await self._cleanup()
    
    def stop(self):
        """Stop the scheduler service."""
        if not self.running:
            return
        
        logger.info("🛑 Stopping Alibaba scheduler...")
        self.running = False
        
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
    
    async def _perform_initial_sync(self):
        """Perform initial sync for all Alibaba accounts that haven't been synced recently."""
        try:
            logger.info("🔄 Performing initial sync check...")
            
            self.db = SessionLocal()
            
            # Find Alibaba platform
            alibaba_platform = self.db.query(Platform).filter(
                Platform.name == "alibaba"
            ).first()
            
            if not alibaba_platform:
                logger.warning("Alibaba platform not found in database")
                return
            
            # Get all active Alibaba accounts
            accounts = self.db.query(PlatformAccount).filter(
                PlatformAccount.platform_id == alibaba_platform.id,
                PlatformAccount.is_active == True
            ).all()
            
            logger.info(f"Found {len(accounts)} active Alibaba accounts")
            
            for account in accounts:
                try:
                    # Check if account needs initial sync (no sync in last 24 hours)
                    needs_initial_sync = (
                        account.last_sync is None or 
                        account.last_sync < (datetime.utcnow() - timedelta(hours=24))
                    )
                    
                    if needs_initial_sync:
                        logger.info(f"Performing initial sync for account {account.id}")
                        sync_service = AlibabaSyncService(self.db)
                        result = await sync_service.sync_account_initial(str(account.id), days_back=7)
                        
                        if result.get("success"):
                            logger.info(f"✅ Initial sync completed for account {account.id}: {result.get('stats')}")
                        else:
                            logger.error(f"❌ Initial sync failed for account {account.id}: {result.get('error')}")
                    else:
                        logger.info(f"Account {account.id} recently synced, skipping initial sync")
                        
                except Exception as e:
                    logger.error(f"Error during initial sync for account {account.id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error during initial sync: {e}")
        finally:
            if self.db:
                self.db.close()
                self.db = None
    
    async def _sync_loop(self):
        """Main sync loop that runs every N minutes."""
        while self.running:
            try:
                # Wait for the sync interval
                await asyncio.sleep(self.sync_interval_minutes * 60)
                
                if not self.running:
                    break
                
                # Perform incremental sync
                await self._perform_incremental_sync()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _perform_incremental_sync(self):
        """Perform incremental sync for all Alibaba accounts."""
        try:
            logger.info("🔄 Performing incremental sync...")
            
            self.db = SessionLocal()
            
            # Find Alibaba platform
            alibaba_platform = self.db.query(Platform).filter(
                Platform.name == "alibaba"
            ).first()
            
            if not alibaba_platform:
                logger.warning("Alibaba platform not found in database")
                return
            
            # Get all active Alibaba accounts
            accounts = self.db.query(PlatformAccount).filter(
                PlatformAccount.platform_id == alibaba_platform.id,
                PlatformAccount.is_active == True
            ).all()
            
            sync_results = []
            
            for account in accounts:
                try:
                    logger.info(f"Syncing account {account.id} ({account.username})")
                    
                    sync_service = AlibabaSyncService(self.db)
                    result = await sync_service.sync_account_incremental(str(account.id))
                    
                    sync_results.append({
                        "account_id": str(account.id),
                        "username": account.username,
                        "result": result
                    })
                    
                    if result.get("success"):
                        stats = result.get('stats', {})
                        logger.info(f"✅ Sync completed for {account.username}: {stats}")
                    else:
                        logger.error(f"❌ Sync failed for {account.username}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error syncing account {account.id}: {e}")
                    continue
            
            # Log overall sync summary
            successful_syncs = sum(1 for r in sync_results if r["result"].get("success"))
            total_new_messages = sum(r["result"].get("stats", {}).get("new_messages", 0) for r in sync_results)
            
            logger.info(f"📊 Sync summary: {successful_syncs}/{len(accounts)} accounts synced, {total_new_messages} new messages")
            
        except Exception as e:
            logger.error(f"Error during incremental sync: {e}")
        finally:
            if self.db:
                self.db.close()
                self.db = None
    
    async def _cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Cleaning up scheduler resources...")
        if self.db:
            self.db.close()
            self.db = None


# CLI interface for running the scheduler
async def main():
    """Main entry point for running the scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alibaba Message Sync Scheduler")
    parser.add_argument(
        "--interval", 
        type=int, 
        default=5, 
        help="Sync interval in minutes (default: 5)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("alibaba_scheduler.log")
        ]
    )
    
    # Create and start scheduler
    scheduler = AlibabaSchedulerService(sync_interval_minutes=args.interval)
    
    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        scheduler.stop()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
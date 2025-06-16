#!/usr/bin/env python3
"""Command-line tool for managing Alibaba message synchronization."""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.alibaba_sync import AlibabaSyncService
from app.services.alibaba_scheduler import AlibabaSchedulerService
from app.models import PlatformAccount, Platform, Chat, Message
from app.db.base import SessionLocal

logger = logging.getLogger(__name__)


class AlibabaSyncManager:
    """Manager for Alibaba sync operations."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    async def run_initial_sync(self, account_id: str = None, days_back: int = 7):
        """Run initial sync for specified account or all accounts."""
        try:
            if account_id:
                # Sync specific account
                logger.info(f"Running initial sync for account {account_id}")
                sync_service = AlibabaSyncService(self.db)
                result = await sync_service.sync_account_initial(account_id, days_back)
                
                if result.get("success"):
                    print(f"✅ Initial sync completed for account {account_id}")
                    print(f"Stats: {result.get('stats')}")
                else:
                    print(f"❌ Initial sync failed: {result.get('error')}")
            else:
                # Sync all Alibaba accounts
                accounts = self._get_alibaba_accounts()
                print(f"Found {len(accounts)} Alibaba accounts")
                
                for account in accounts:
                    print(f"\n🔄 Syncing account {account.id} ({account.username})")
                    sync_service = AlibabaSyncService(self.db)
                    result = await sync_service.sync_account_initial(str(account.id), days_back)
                    
                    if result.get("success"):
                        print(f"✅ Success: {result.get('stats')}")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Error running initial sync: {e}")
            print(f"❌ Error: {e}")
    
    async def run_incremental_sync(self, account_id: str = None):
        """Run incremental sync for specified account or all accounts."""
        try:
            if account_id:
                # Sync specific account
                logger.info(f"Running incremental sync for account {account_id}")
                sync_service = AlibabaSyncService(self.db)
                result = await sync_service.sync_account_incremental(account_id)
                
                if result.get("success"):
                    print(f"✅ Incremental sync completed for account {account_id}")
                    print(f"Stats: {result.get('stats')}")
                else:
                    print(f"❌ Incremental sync failed: {result.get('error')}")
            else:
                # Sync all Alibaba accounts
                accounts = self._get_alibaba_accounts()
                print(f"Found {len(accounts)} Alibaba accounts")
                
                for account in accounts:
                    print(f"\n🔄 Syncing account {account.id} ({account.username})")
                    sync_service = AlibabaSyncService(self.db)
                    result = await sync_service.sync_account_incremental(str(account.id))
                    
                    if result.get("success"):
                        print(f"✅ Success: {result.get('stats')}")
                    else:
                        print(f"❌ Failed: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Error running incremental sync: {e}")
            print(f"❌ Error: {e}")
    
    async def start_scheduler(self, interval_minutes: int = 5):
        """Start the periodic sync scheduler."""
        print(f"🚀 Starting Alibaba scheduler (sync every {interval_minutes} minutes)")
        print("Press Ctrl+C to stop")
        
        scheduler = AlibabaSchedulerService(sync_interval_minutes=interval_minutes)
        await scheduler.start()
    
    def show_stats(self, account_id: str = None):
        """Show sync statistics."""
        try:
            if account_id:
                account = self.db.query(PlatformAccount).filter(
                    PlatformAccount.id == account_id
                ).first()
                
                if not account:
                    print(f"❌ Account {account_id} not found")
                    return
                
                self._show_account_stats(account)
            else:
                accounts = self._get_alibaba_accounts()
                print(f"📊 Alibaba Sync Statistics ({len(accounts)} accounts)\n")
                
                for account in accounts:
                    self._show_account_stats(account)
                    print()
        
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            print(f"❌ Error: {e}")
    
    def list_accounts(self):
        """List all Alibaba accounts."""
        try:
            accounts = self._get_alibaba_accounts()
            
            print(f"📋 Alibaba Accounts ({len(accounts)} total)\n")
            
            for account in accounts:
                status = "🟢 Active" if account.is_active else "🔴 Inactive"
                last_sync = account.last_sync.strftime("%Y-%m-%d %H:%M:%S") if account.last_sync else "Never"
                error_count = account.error_count or 0
                
                print(f"ID: {account.id}")
                print(f"Username: {account.username}")
                print(f"Status: {status}")
                print(f"Last Sync: {last_sync}")
                print(f"Error Count: {error_count}")
                print("-" * 40)
        
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            print(f"❌ Error: {e}")
    
    def _get_alibaba_accounts(self):
        """Get all Alibaba accounts."""
        alibaba_platform = self.db.query(Platform).filter(
            Platform.name == "alibaba"
        ).first()
        
        if not alibaba_platform:
            return []
        
        return self.db.query(PlatformAccount).filter(
            PlatformAccount.platform_id == alibaba_platform.id,
            PlatformAccount.is_active == True
        ).all()
    
    def _show_account_stats(self, account: PlatformAccount):
        """Show statistics for a single account."""
        # Get chat count
        chat_count = self.db.query(Chat).filter(
            Chat.account_id == account.id
        ).count()
        
        # Get message count
        message_count = self.db.query(Message).join(Chat).filter(
            Chat.account_id == account.id
        ).count()
        
        # Get recent message count (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_message_count = self.db.query(Message).join(Chat).filter(
            Chat.account_id == account.id,
            Message.created_at >= yesterday
        ).count()
        
        # Format last sync time
        last_sync = account.last_sync.strftime("%Y-%m-%d %H:%M:%S") if account.last_sync else "Never"
        
        # Account status
        status = "🟢 Active" if account.is_active else "🔴 Inactive"
        
        print(f"Account: {account.username} ({account.id})")
        print(f"Status: {status}")
        print(f"Last Sync: {last_sync}")
        print(f"Error Count: {account.error_count or 0}")
        print(f"Chats: {chat_count}")
        print(f"Total Messages: {message_count}")
        print(f"Messages (24h): {recent_message_count}")
    
    def close(self):
        """Close database connection."""
        self.db.close()


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Alibaba Message Sync Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Initial sync command
    initial_parser = subparsers.add_parser("initial", help="Run initial sync")
    initial_parser.add_argument("--account", help="Specific account ID to sync")
    initial_parser.add_argument("--days", type=int, default=7, help="Days back to sync (default: 7)")
    
    # Incremental sync command
    incremental_parser = subparsers.add_parser("incremental", help="Run incremental sync")
    incremental_parser.add_argument("--account", help="Specific account ID to sync")
    
    # Scheduler command
    scheduler_parser = subparsers.add_parser("scheduler", help="Start periodic sync scheduler")
    scheduler_parser.add_argument("--interval", type=int, default=5, help="Sync interval in minutes (default: 5)")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show sync statistics")
    stats_parser.add_argument("--account", help="Specific account ID to show stats for")
    
    # List accounts command
    subparsers.add_parser("accounts", help="List all Alibaba accounts")
    
    # Global options
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create manager
    manager = AlibabaSyncManager()
    
    try:
        if args.command == "initial":
            await manager.run_initial_sync(args.account, args.days)
        elif args.command == "incremental":
            await manager.run_incremental_sync(args.account)
        elif args.command == "scheduler":
            await manager.start_scheduler(args.interval)
        elif args.command == "stats":
            manager.show_stats(args.account)
        elif args.command == "accounts":
            manager.list_accounts()
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")
    finally:
        manager.close()


if __name__ == "__main__":
    asyncio.run(main())
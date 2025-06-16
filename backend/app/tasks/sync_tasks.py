from celery import shared_task
from datetime import datetime, timedelta
import logging

from app.db.base import SessionLocal
from app.models import PlatformAccount, Chat, Message
from app.services.platform_sync import PlatformSyncService
from app.core.config import settings

logger = logging.getLogger(__name__)


@shared_task
def sync_all_platforms():
    """Sync messages from all active platform accounts."""
    db = SessionLocal()
    try:
        accounts = db.query(PlatformAccount).filter(
            PlatformAccount.is_active == True
        ).all()
        
        for account in accounts:
            sync_platform_account.delay(str(account.id))
            
        return f"Queued sync for {len(accounts)} accounts"
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def sync_platform_account(self, account_id: str):
    """Sync messages for a specific platform account."""
    db = SessionLocal()
    try:
        account = db.query(PlatformAccount).filter(
            PlatformAccount.id == account_id
        ).first()
        
        if not account:
            return f"Account {account_id} not found"
            
        sync_service = PlatformSyncService(db)
        result = sync_service.sync_account(account)
        
        # Update last sync time
        account.last_sync = datetime.utcnow()
        account.error_count = 0
        db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {str(e)}")
        
        # Update error count with exponential backoff
        if account:
            account.error_count += 1
            account.last_error = str(e)
            db.commit()
            
            # Retry with exponential backoff
            retry_delay = min(
                settings.RATE_LIMIT_INITIAL_DELAY * (settings.RATE_LIMIT_BACKOFF_FACTOR ** account.error_count),
                settings.RATE_LIMIT_MAX_DELAY
            )
            
            raise self.retry(countdown=retry_delay, exc=e)
    finally:
        db.close()


@shared_task
def archive_old_messages():
    """Archive messages older than configured days."""
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=settings.ARCHIVE_AFTER_DAYS)
        
        # Find chats to archive (not starred, not in history section)
        chats_to_archive = db.query(Chat).filter(
            Chat.is_starred == False,
            Chat.is_archived == False,
            Chat.last_message_at < cutoff_date
        ).all()
        
        archived_count = 0
        for chat in chats_to_archive:
            chat.is_archived = True
            archived_count += 1
            
        db.commit()
        
        return f"Archived {archived_count} chats"
    finally:
        db.close()
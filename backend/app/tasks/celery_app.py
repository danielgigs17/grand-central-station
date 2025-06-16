from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "grand_central",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.sync_tasks", "app.tasks.automation_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "sync-all-platforms": {
        "task": "app.tasks.sync_tasks.sync_all_platforms",
        "schedule": settings.MESSAGE_CHECK_INTERVAL,
    },
    "archive-old-messages": {
        "task": "app.tasks.sync_tasks.archive_old_messages",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
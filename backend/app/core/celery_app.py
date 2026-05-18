from celery import Celery
from celery.schedules import crontab
from app.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "dispose_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    "auto-dispatch-pickups": {
        "task": "app.services.auto_dispatch.tasks.run_auto_dispatch_all_orgs",
        "schedule": crontab(minute="*/1"), # Every 1 minute
    },
    "aggregate-hourly-metrics": {
        "task": "app.services.analytics.tasks.aggregate_hourly_metrics",
        "schedule": crontab(minute=0), # Every hour
    },
    "aggregate-daily-metrics-midnight": {
        "task": "app.services.analytics.tasks.aggregate_daily_metrics",
        "schedule": crontab(hour=0, minute=0),
    },
    "aggregate-weekly-metrics-monday": {
        "task": "app.services.analytics.tasks.aggregate_weekly_metrics",
        "schedule": crontab(hour=0, minute=5, day_of_week="monday"),
    },
    "cleanup-stale-fleet-sessions": {
        "task": "app.services.fleet.tasks.cleanup_stale_fleet_sessions",
        "schedule": crontab(minute="*/15"), # Every 15 minutes
    },
    "process-dunning-daily": {
        "task": "app.tasks.subscription_tasks.process_dunning_and_suspensions",
        "schedule": crontab(hour=0, minute=0), # Daily at midnight
    },
}


celery_app.autodiscover_tasks([
    "app.services.analytics", 
    "app.services.fleet", 
    "app.services.auto_dispatch",
    "app.tasks"
])

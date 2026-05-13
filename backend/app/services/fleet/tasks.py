from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.fleet_repo import FleetRepository
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def cleanup_stale_fleet_sessions():
    """
    Periodic task to mark drivers as offline if they haven't sent a heartbeat.
    """
    db = SessionLocal()
    try:
        logger.info("Running stale fleet session cleanup...")
        FleetRepository.close_stale_sessions(db, timeout_minutes=15)
        db.commit()
        logger.info("Cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Error during fleet cleanup: {e}")
        db.rollback()
    finally:
        db.close()

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.organization import Organization
from app.services.auto_dispatch_service import AutoDispatchEngine
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def run_auto_dispatch_all_orgs():
    """
    Periodic task that runs the Auto-Dispatch engine for all active organizations.
    Recommended frequency: Every 1-5 minutes.
    """
    db = SessionLocal()
    try:
        # 1. Fetch all organization IDs
        organizations = db.query(Organization.id).all()
        
        if not organizations:
            logger.info("[AUTO_DISPATCH_TASK] No organizations found for dispatching.")
            return

        # 2. Identify a 'System' user for logging purposes
        system_user = db.query(User).filter(User.email.like("%system%")).first()

        engine = AutoDispatchEngine(db)
        total_assigned = 0

        for org_row in organizations:
            org_id = org_row[0]
            try:
                # Process up to 50 pickups per organization in this cycle
                count = engine.run_dispatch_cycle(
                    organization_id=org_id,
                    system_user=system_user,
                    batch_size=50
                )
                total_assigned += count
            except Exception as org_err:
                logger.error(f"[AUTO_DISPATCH_TASK] Failed for Org {org_id}: {org_err}")
                continue

        logger.info(f"[AUTO_DISPATCH_TASK] Cycle complete. Total pickups auto-assigned: {total_assigned}")

    except Exception as e:
        logger.error(f"[AUTO_DISPATCH_TASK] Critical failure in dispatch loop: {e}")
    finally:
        db.close()

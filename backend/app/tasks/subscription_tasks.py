from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.notification import Notification
from app.utils.enums import NotificationType, NotificationStatus
from app.models.role_mapping import UserRole
from app.services.audit_service import AuditService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.subscription_tasks.process_dunning")
def process_dunning() -> dict:
    """
    Daily Celery Task to process dunning.
    Scans for subscriptions currently in GRACE period that have exceeded their grace_period_end,
    transitions them to SUSPENDED, logs audit trials, and notifies organization users.
    """
    return _run_dunning_logic()

@celery_app.task(name="app.tasks.subscription_tasks.process_dunning_and_suspensions")
def process_dunning_and_suspensions() -> dict:
    """
    Daily Celery Task to process dunning and suspensions (alias).
    """
    return _run_dunning_logic()

def _run_dunning_logic() -> dict:
    db = SessionLocal()
    audit_svc = AuditService(db)
    suspended_count = 0
    
    try:
        now = datetime.utcnow()
        # Find grace subscriptions that have expired
        expired_grace_subs = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.GRACE,
            Subscription.grace_period_end <= now
        ).all()
        
        for sub in expired_grace_subs:
            # 1. Transition to SUSPENDED
            sub.status = SubscriptionStatus.SUSPENDED
            
            # 2. Add System Audit Log
            audit_svc.log_action(
                user_id=sub.organization_id,
                action="subscription.suspended_due_to_nonpayment",
                org_id=sub.organization_id,
                meta={
                    "subscription_id": sub.id,
                    "grace_period_end": sub.grace_period_end.isoformat() if sub.grace_period_end else None,
                    "suspended_at": now.isoformat()
                }
            )
            
            # 3. Create System Alert Notifications for organization members
            org_users = db.query(UserRole).filter(UserRole.org_id == sub.organization_id).all()
            for mapping in org_users:
                alert = Notification(
                    organization_id=sub.organization_id,
                    user_id=mapping.user_id,
                    title="🚨 Subscription Suspended",
                    message="Your organization's subscription has been suspended due to outstanding payment renewal. Please complete payment to restore access.",
                    type=NotificationType.SYSTEM,
                    status=NotificationStatus.UNREAD
                )
                db.add(alert)
                
            suspended_count += 1
            logger.info(f"Subscription ID {sub.id} of Organization {sub.organization_id} has been SUSPENDED due to dunning failure.")
            
        db.commit()
        return {"processed": len(expired_grace_subs), "suspended": suspended_count}
        
    except Exception as e:
        db.rollback()
        logger.exception("Failed to run daily process_dunning_and_suspensions task.")
        raise e
    finally:
        db.close()

"""
Celery tasks for asynchronous multi-channel notification delivery.
Handles Email (SMTP) and Push (FCM) channels with delivery logging,
user preference enforcement, and automatic retry logic.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.notification import Notification, NotificationDeliveryLog, UserNotificationPreference
from app.models.user import User
from app.utils.enums import DeliveryChannel, DeliveryStatus, NotificationCategory
from app.services.email_service import send_notification_email

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.notification_tasks.send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_notification(self, notification_id: str, user_id: int, organization_id: int):
    """
    Send an email notification for a given notification record.
    Respects user preferences, logs delivery status, and retries on failure.
    """
    db = SessionLocal()
    try:
        # 1. Fetch the notification
        notif = db.query(Notification).filter(Notification.id == UUID(notification_id)).first()
        if not notif:
            logger.warning(f"Notification {notification_id} not found. Skipping email delivery.")
            return {"status": "skipped", "reason": "notification_not_found"}

        # 2. Check user email preference for this notification category
        pref = db.query(UserNotificationPreference).filter(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.category == notif.category,
        ).first()

        if pref and not pref.email_enabled:
            # User has disabled email for this category — log as SKIPPED
            log_entry = NotificationDeliveryLog(
                notification_id=notif.id,
                channel=DeliveryChannel.EMAIL,
                delivery_status=DeliveryStatus.SKIPPED,
                error_message="User preference: email disabled for this category",
                provider="SMTP",
            )
            db.add(log_entry)
            db.commit()
            logger.info(f"Email skipped for notification {notification_id}: user preference disabled")
            return {"status": "skipped", "reason": "preference_disabled"}

        # 3. Get user email address
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            log_entry = NotificationDeliveryLog(
                notification_id=notif.id,
                channel=DeliveryChannel.EMAIL,
                delivery_status=DeliveryStatus.SKIPPED,
                error_message="User has no email address configured",
                provider="SMTP",
            )
            db.add(log_entry)
            db.commit()
            logger.info(f"Email skipped for notification {notification_id}: no email address")
            return {"status": "skipped", "reason": "no_email"}

        # 4. Send the email
        severity_str = notif.severity.value if hasattr(notif.severity, "value") else str(notif.severity)
        category_str = notif.category.value if hasattr(notif.category, "value") else str(notif.category)

        result = send_notification_email(
            to_email=user.email,
            title=notif.title,
            message=notif.message,
            severity=severity_str,
            category=category_str,
        )

        # 5. Log the delivery result
        if result["success"]:
            log_entry = NotificationDeliveryLog(
                notification_id=notif.id,
                channel=DeliveryChannel.EMAIL,
                delivery_status=DeliveryStatus.SENT,
                provider=result.get("provider", "SMTP"),
                sent_at=datetime.now(timezone.utc),
            )
            db.add(log_entry)
            db.commit()
            logger.info(f"Email sent for notification {notification_id} to {user.email}")
            return {"status": "sent", "to": user.email}
        else:
            # Log as FAILED and retry
            log_entry = NotificationDeliveryLog(
                notification_id=notif.id,
                channel=DeliveryChannel.EMAIL,
                delivery_status=DeliveryStatus.FAILED,
                error_message=result.get("error", "Unknown error"),
                provider=result.get("provider", "SMTP"),
                retry_count=self.request.retries,
            )
            db.add(log_entry)
            db.commit()

            # Retry the task
            raise self.retry(exc=Exception(result.get("error", "Email send failed")))

    except Exception as e:
        if self.request.retries >= self.max_retries:
            logger.error(f"Email delivery permanently failed for notification {notification_id}: {e}")
            # Log final failure
            try:
                log_entry = NotificationDeliveryLog(
                    notification_id=UUID(notification_id),
                    channel=DeliveryChannel.EMAIL,
                    delivery_status=DeliveryStatus.FAILED,
                    error_message=f"Max retries exceeded: {str(e)}",
                    provider="SMTP",
                    retry_count=self.request.retries,
                )
                db.add(log_entry)
                db.commit()
            except Exception:
                pass
            return {"status": "failed", "error": str(e)}
        raise
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.notification_tasks.send_push_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_push_notification(self, notification_id: str, user_id: int, organization_id: int):
    """
    Send a push notification via Firebase Cloud Messaging (FCM).
    Currently a structured placeholder — ready for FCM SDK integration.
    Respects user preferences and logs delivery status.
    """
    db = SessionLocal()
    try:
        # 1. Fetch the notification
        notif = db.query(Notification).filter(Notification.id == UUID(notification_id)).first()
        if not notif:
            logger.warning(f"Notification {notification_id} not found. Skipping push delivery.")
            return {"status": "skipped", "reason": "notification_not_found"}

        # 2. Check user push preference for this notification category
        pref = db.query(UserNotificationPreference).filter(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.category == notif.category,
        ).first()

        if pref and not pref.push_enabled:
            log_entry = NotificationDeliveryLog(
                notification_id=notif.id,
                channel=DeliveryChannel.PUSH,
                delivery_status=DeliveryStatus.SKIPPED,
                error_message="User preference: push disabled for this category",
                provider="FCM",
            )
            db.add(log_entry)
            db.commit()
            logger.info(f"Push skipped for notification {notification_id}: user preference disabled")
            return {"status": "skipped", "reason": "preference_disabled"}

        # 3. Build FCM payload (ready for SDK integration)
        from app.core.config import FCM_SERVER_KEY
        
        if not FCM_SERVER_KEY:
            log_entry = NotificationDeliveryLog(
                notification_id=notif.id,
                channel=DeliveryChannel.PUSH,
                delivery_status=DeliveryStatus.SKIPPED,
                error_message="FCM server key not configured",
                provider="FCM",
            )
            db.add(log_entry)
            db.commit()
            logger.info(f"Push skipped for notification {notification_id}: FCM not configured")
            return {"status": "skipped", "reason": "fcm_not_configured"}

        # 4. FCM HTTP v1 API integration point
        # TODO: When Firebase Admin SDK or HTTP v1 is integrated:
        #   - Fetch user's FCM device tokens from a UserDevice table
        #   - Build message payload with notification + data sections
        #   - Send via firebase_admin.messaging.send()
        #
        # Example payload structure:
        # fcm_payload = {
        #     "message": {
        #         "token": user_device_token,
        #         "notification": {
        #             "title": notif.title,
        #             "body": notif.message,
        #         },
        #         "data": {
        #             "notification_id": str(notif.id),
        #             "category": notif.category.value,
        #             "severity": notif.severity.value,
        #             "click_action": "NOTIFICATION_CLICK",
        #         },
        #     }
        # }

        severity_str = notif.severity.value if hasattr(notif.severity, "value") else str(notif.severity)
        category_str = notif.category.value if hasattr(notif.category, "value") else str(notif.category)

        logger.info(
            f"Push notification queued for user {user_id}: "
            f"title='{notif.title}', severity={severity_str}, category={category_str}"
        )

        log_entry = NotificationDeliveryLog(
            notification_id=notif.id,
            channel=DeliveryChannel.PUSH,
            delivery_status=DeliveryStatus.PENDING,
            provider="FCM",
            error_message="FCM SDK integration pending — payload structured and ready",
        )
        db.add(log_entry)
        db.commit()
        return {"status": "pending", "reason": "fcm_sdk_pending"}

    except Exception as e:
        logger.error(f"Push delivery failed for notification {notification_id}: {e}")
        try:
            log_entry = NotificationDeliveryLog(
                notification_id=UUID(notification_id),
                channel=DeliveryChannel.PUSH,
                delivery_status=DeliveryStatus.FAILED,
                error_message=str(e),
                provider="FCM",
                retry_count=self.request.retries,
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            pass
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.notification_tasks.dispatch_multi_channel")
def dispatch_multi_channel(notification_id: str, user_id: int, organization_id: int):
    """
    Master dispatcher: Queues email and push delivery tasks in parallel.
    In-app delivery is already handled by the WebSocket layer (Step 2).
    This task logs the IN_APP delivery as DELIVERED and fans-out to Email + Push.
    """
    db = SessionLocal()
    try:
        notif = db.query(Notification).filter(Notification.id == UUID(notification_id)).first()
        if not notif:
            return {"status": "skipped", "reason": "notification_not_found"}

        # Log IN_APP as delivered (WebSocket handled this in real-time)
        in_app_pref = db.query(UserNotificationPreference).filter(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.category == notif.category,
        ).first()

        if in_app_pref and not in_app_pref.in_app_enabled:
            in_app_status = DeliveryStatus.SKIPPED
            in_app_error = "User preference: in-app disabled for this category"
        else:
            in_app_status = DeliveryStatus.DELIVERED
            in_app_error = None

        in_app_log = NotificationDeliveryLog(
            notification_id=notif.id,
            channel=DeliveryChannel.IN_APP,
            delivery_status=in_app_status,
            provider="WEBSOCKET",
            error_message=in_app_error,
            delivered_at=datetime.now(timezone.utc) if in_app_status == DeliveryStatus.DELIVERED else None,
        )
        db.add(in_app_log)
        db.commit()

        # Fan-out to email and push channels
        send_email_notification.delay(notification_id, user_id, organization_id)
        send_push_notification.delay(notification_id, user_id, organization_id)

        logger.info(f"Multi-channel dispatch triggered for notification {notification_id}")
        return {"status": "dispatched", "channels": ["IN_APP", "EMAIL", "PUSH"]}

    except Exception as e:
        logger.error(f"Multi-channel dispatch failed for notification {notification_id}: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()

from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status

from app.models.notification import Notification, UserNotificationPreference, NotificationDeliveryLog
from app.repositories.notification_repo import NotificationRepository
from app.utils.enums import NotificationStatus, NotificationSeverity, NotificationCategory, DeliveryChannel, DeliveryStatus, NotificationType


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)

    def get_user_notifications(
        self,
        organization_id: int,
        user_id: int,
        status: Optional[NotificationStatus] = None,
        severity: Optional[NotificationSeverity] = None,
        category: Optional[NotificationCategory] = None,
        archived: Optional[bool] = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        return self.repo.get_user_notifications(
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            severity=severity,
            category=category,
            archived=archived,
            search=search,
            skip=skip,
            limit=limit,
        )

    def get_unread_count(
        self,
        organization_id: int,
        user_id: int,
        archived: Optional[bool] = False,
    ) -> int:
        return self.repo.count_unread_notifications(
            user_id=user_id,
            organization_id=organization_id,
            archived=archived,
        )

    def mark_notification_read(
        self,
        notification_id: UUID,
        organization_id: int,
        user_id: int,
    ) -> Notification:
        notification = self.repo.get_notification_by_id(notification_id, organization_id)
        if not notification or notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(timezone.utc)
        self.db.flush()
        return notification

    def mark_all_notifications_read(
        self,
        organization_id: int,
        user_id: int,
    ) -> int:
        return self.repo.mark_all_notifications_read(
            user_id=user_id,
            organization_id=organization_id,
        )

    def archive_notification(
        self,
        notification_id: UUID,
        organization_id: int,
        user_id: int,
    ) -> Notification:
        notification = self.repo.get_notification_by_id(notification_id, organization_id)
        if not notification or notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        notification.archived = True
        self.db.flush()
        return notification

    def archive_all_notifications(
        self,
        organization_id: int,
        user_id: int,
    ) -> int:
        return self.repo.archive_all_notifications(
            user_id=user_id,
            organization_id=organization_id,
        )

    def get_entity_notifications(
        self,
        organization_id: int,
        entity_type: str,
        entity_id: UUID,
    ) -> List[Notification]:
        return self.repo.get_notifications_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=organization_id,
        )

    # --- User Notification Preferences Logic ---

    def get_user_preferences(
        self,
        user_id: int,
        organization_id: int,
    ) -> List[UserNotificationPreference]:
        # Fetch existing preferences
        prefs = self.repo.get_user_preferences(user_id, organization_id)
        pref_categories = {p.category for p in prefs}

        # Auto-initialize preferences for any missing categories
        initialized = False
        for cat in NotificationCategory:
            if cat not in pref_categories:
                new_pref = UserNotificationPreference(
                    user_id=user_id,
                    organization_id=organization_id,
                    category=cat,
                    in_app_enabled=True,
                    email_enabled=True,
                    push_enabled=True,
                )
                self.repo.create_user_preference(new_pref)
                prefs.append(new_pref)
                initialized = True

        if initialized:
            self.db.flush()

        return prefs

    def update_user_preference(
        self,
        user_id: int,
        organization_id: int,
        category: NotificationCategory,
        in_app_enabled: Optional[bool] = None,
        email_enabled: Optional[bool] = None,
        push_enabled: Optional[bool] = None,
    ) -> UserNotificationPreference:
        pref = self.repo.get_preference_by_category(user_id, category)
        
        if not pref:
            # Create a fresh preference setting
            pref = UserNotificationPreference(
                user_id=user_id,
                organization_id=organization_id,
                category=category,
                in_app_enabled=True,
                email_enabled=True,
                push_enabled=True,
            )
            self.repo.create_user_preference(pref)

        if in_app_enabled is not None:
            pref.in_app_enabled = in_app_enabled
        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if push_enabled is not None:
            pref.push_enabled = push_enabled

        self.db.flush()
        return pref

    # --- Delivery Logging & Multi-Channel ---

    def get_delivery_logs(
        self,
        notification_id: UUID,
    ) -> List[NotificationDeliveryLog]:
        """Retrieve all delivery logs for a given notification."""
        return (
            self.db.query(NotificationDeliveryLog)
            .filter(NotificationDeliveryLog.notification_id == notification_id)
            .order_by(NotificationDeliveryLog.created_at.desc())
            .all()
        )

    def get_delivery_summary(
        self,
        organization_id: int,
        user_id: int,
    ) -> dict:
        """
        Return aggregated delivery statistics for all notifications
        belonging to a user within their organization.
        """
        from sqlalchemy import func as sqlfunc

        # Get all notification IDs for this user + org
        notif_ids_select = (
            self.db.query(Notification.id)
            .filter(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
            )
            .statement
        )

        # Aggregate delivery logs
        logs = (
            self.db.query(
                NotificationDeliveryLog.channel,
                NotificationDeliveryLog.delivery_status,
                sqlfunc.count(NotificationDeliveryLog.id).label("count"),
            )
            .filter(NotificationDeliveryLog.notification_id.in_(notif_ids_select))
            .group_by(
                NotificationDeliveryLog.channel,
                NotificationDeliveryLog.delivery_status,
            )
            .all()
        )

        summary = {}
        for channel, delivery_status, count in logs:
            ch_key = channel.value if hasattr(channel, "value") else str(channel)
            st_key = delivery_status.value if hasattr(delivery_status, "value") else str(delivery_status)
            if ch_key not in summary:
                summary[ch_key] = {}
            summary[ch_key][st_key] = count

        return summary

    def dispatch_notification(
        self,
        notification_id: UUID,
        user_id: int,
        organization_id: int,
    ):
        """
        Manually trigger multi-channel dispatch for a notification.
        Useful for re-sending failed deliveries.
        """
        try:
            from app.tasks.notification_tasks import dispatch_multi_channel
            dispatch_multi_channel.delay(
                str(notification_id),
                user_id,
                organization_id,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to queue multi-channel dispatch: {e}")

    def get_notification_metrics(self, user_id: int, organization_id: int) -> dict:
        """
        Get aggregated notification and delivery metrics for active analytics.
        """
        return self.repo.get_notification_metrics(user_id, organization_id)

    def delete_notification(
        self,
        notification_id: UUID,
        organization_id: int,
        user_id: int,
    ) -> bool:
        """
        Permanently delete a notification and commit the transaction.
        """
        notification = self.repo.get_notification_by_id(notification_id, organization_id)
        if not notification or notification.user_id != user_id:
            return False
        
        self.repo.delete_notification(notification)
        self.db.commit()
        return True

    async def create_test_notification(
        self,
        organization_id: int,
        user_id: int,
        title: str,
        message: str,
        severity: NotificationSeverity,
        category: NotificationCategory,
    ) -> Notification:
        """
        Creates a test notification and dispatches it in real-time
        via WebSockets and asynchronous multi-channel delivery.
        """
        notification = Notification(
            organization_id=organization_id,
            user_id=user_id,
            title=title,
            message=message,
            type=NotificationType.SYSTEM,
            status=NotificationStatus.UNREAD,
            severity=severity,
            category=category,
            source_service="ADMIN_CONSOLE",
            archived=False,
        )
        self.repo.create_notification(notification)
        self.db.commit()

        # Publish the created notification via Redis PubSub for real-time WebSocket delivery
        try:
            from app.core.pubsub import pubsub_service
            unread_count = self.get_unread_count(organization_id, user_id)
            await pubsub_service.publish(f"notifications:user_{user_id}", {
                "event": "notification_new",
                "organization_id": organization_id,
                "user_id": user_id,
                "data": {
                    "notification": {
                        "id": str(notification.id),
                        "organization_id": notification.organization_id,
                        "user_id": notification.user_id,
                        "title": notification.title,
                        "message": notification.message,
                        "type": notification.type.value if hasattr(notification.type, "value") else str(notification.type),
                        "status": notification.status.value if hasattr(notification.status, "value") else str(notification.status),
                        "severity": notification.severity.value if hasattr(notification.severity, "value") else str(notification.severity),
                        "category": notification.category.value if hasattr(notification.category, "value") else str(notification.category),
                        "source_service": notification.source_service,
                        "archived": notification.archived,
                        "created_at": notification.created_at.isoformat() if notification.created_at else None,
                    },
                    "unread_count": unread_count
                }
            })
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to publish test notification to Redis: {e}")

        # Dispatch via multi-channel Celery worker task (email + push)
        self.dispatch_notification(notification.id, user_id, organization_id)

        return notification



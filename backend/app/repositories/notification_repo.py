from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, or_

from app.models.notification import Notification, NotificationDeliveryLog, UserNotificationPreference
from app.utils.enums import NotificationStatus, NotificationType, NotificationSeverity, NotificationCategory


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_notification_by_id(
        self,
        notification_id: UUID,
        organization_id: int,
    ) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == organization_id,
        )
        return self.db.scalar(stmt)

    def get_user_notifications(
        self,
        user_id: int,
        organization_id: int,
        status: Optional[NotificationStatus] = None,
        severity: Optional[NotificationSeverity] = None,
        category: Optional[NotificationCategory] = None,
        archived: Optional[bool] = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
        )

        if archived is not None:
            stmt = stmt.where(Notification.archived == archived)

        if status is not None:
            stmt = stmt.where(Notification.status == status)

        if severity is not None:
            stmt = stmt.where(Notification.severity == severity)

        if category is not None:
            stmt = stmt.where(Notification.category == category)

        if search is not None and search.strip() != "":
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Notification.title.ilike(search_pattern),
                    Notification.message.ilike(search_pattern),
                )
            )

        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_unread_notifications(
        self,
        user_id: int,
        organization_id: int,
        archived: Optional[bool] = False,
    ) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.status == NotificationStatus.UNREAD,
        )
        if archived is not None:
            stmt = stmt.where(Notification.archived == archived)

        return self.db.scalar(stmt) or 0

    def mark_notification_read(self, notification: Notification) -> Notification:
        notification.status = NotificationStatus.READ
        self.db.flush()
        return notification

    def mark_all_notifications_read(
        self,
        user_id: int,
        organization_id: int,
    ) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .values(status=NotificationStatus.READ)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount or 0

    def archive_notification(self, notification: Notification) -> Notification:
        notification.archived = True
        self.db.flush()
        return notification

    def archive_all_notifications(
        self,
        user_id: int,
        organization_id: int,
    ) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.archived == False,
            )
            .values(archived=True)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount or 0

    def get_notifications_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        organization_id: int,
    ) -> List[Notification]:
        stmt = (
            select(Notification)
            .where(
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
                Notification.organization_id == organization_id,
            )
            .order_by(Notification.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def delete_notification(self, notification: Notification):
        self.db.delete(notification)
        self.db.flush()

    def create_delivery_log(self, log: NotificationDeliveryLog) -> NotificationDeliveryLog:
        self.db.add(log)
        self.db.flush()
        return log

    def get_delivery_logs(self, notification_id: UUID) -> List[NotificationDeliveryLog]:
        stmt = select(NotificationDeliveryLog).where(
            NotificationDeliveryLog.notification_id == notification_id
        ).order_by(NotificationDeliveryLog.created_at.desc())
        return list(self.db.scalars(stmt).all())

    # --- User Notification Preferences Operations ---

    def get_user_preferences(
        self,
        user_id: int,
        organization_id: int,
    ) -> List[UserNotificationPreference]:
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.organization_id == organization_id,
        )
        return list(self.db.scalars(stmt).all())

    def get_preference_by_category(
        self,
        user_id: int,
        category: NotificationCategory,
    ) -> Optional[UserNotificationPreference]:
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.category == category,
        )
        return self.db.scalar(stmt)

    def create_user_preference(
        self,
        preference: UserNotificationPreference,
    ) -> UserNotificationPreference:
        self.db.add(preference)
        self.db.flush()
        return preference

    def get_notification_metrics(self, user_id: int, organization_id: int) -> dict:
        """Calculate high-performance notifications delivery and reading analytics."""
        # Total notifications count
        total = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
        ).scalar() or 0

        # Unread notifications count
        unread = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.status == NotificationStatus.UNREAD,
            Notification.archived == False,
        ).scalar() or 0

        # Archived count
        archived = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.archived == True,
        ).scalar() or 0

        # Read notifications count
        read_count = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.status == NotificationStatus.READ,
        ).scalar() or 0

        # Read rate calculation
        read_rate = 0.0
        if total > 0:
            read_rate = round((read_count / total) * 100, 2)

        # Most active categories
        categories = (
            self.db.query(Notification.category, func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
            )
            .group_by(Notification.category)
            .all()
        )
        category_breakdown = {cat.value if hasattr(cat, "value") else str(cat): count for cat, count in categories}

        # Severity breakdown
        severities = (
            self.db.query(Notification.severity, func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
            )
            .group_by(Notification.severity)
            .all()
        )
        severity_breakdown = {sev.value if hasattr(sev, "value") else str(sev): count for sev, count in severities}

        return {
            "total_notifications": total,
            "unread_count": unread,
            "archived_count": archived,
            "read_rate": read_rate,
            "category_breakdown": category_breakdown,
            "severity_breakdown": severity_breakdown,
        }
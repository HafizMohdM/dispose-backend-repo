from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime, timezone

from app.models.notification import Notification
from app.utils.enums import NotificationStatus


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_notifications(
        self,
        organization_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ):
        return (
            self.db.query(Notification)
            .filter(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
            )
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_unread_count(self, organization_id: int, user_id: int) -> int:
        return (
            self.db.query(func.count(Notification.id))
            .filter(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .scalar()
        )

    def mark_notification_read(
        self,
        notification_id: UUID,
        organization_id: int,
        user_id: int,
    ) -> Notification:
        notification = (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
            )
            .first()
        )

        if not notification:
            raise Exception("Notification not found")

        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(timezone.utc)
        return notification

    def mark_all_notifications_read(
        self,
        organization_id: int,
        user_id: int,
    ) -> int:
        count = (
            self.db.query(Notification)
            .filter(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .update(
                {
                    Notification.status: NotificationStatus.READ,
                    Notification.read_at: datetime.now(timezone.utc),
                },
                synchronize_session="fetch",
            )
        )
        return count

    def get_entity_notifications(
        self,
        organization_id: int,
        entity_type: str,
        entity_id: UUID,
    ):
        return (
            self.db.query(Notification)
            .filter(
                Notification.organization_id == organization_id,
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
            )
            .order_by(Notification.created_at.desc())
            .all()
        )

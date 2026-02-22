from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, update, func

from app.models.notification import Notification, NotificationLog
from app.utils.enums import NotificationStatus, NotificationType


class NotificationRepository:
    def __init__(self, db:Session):
        self.db =db

    def create_notification(
        self,
        notification: Notification,
    ) -> Notification:

        self.db.add(notification)
        self.db.flush()

        return notification


    def get_notification_by_id(
        self,
        notification_id:UUID,
        organization_id:int,
    ) -> Optional[Notification]:

        stmt= select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == organization_id,
        )

        return self.db.scalar(stmt)


    def get_user_notifications(
        self,
        user_id: int,
        organization_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:

        stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
            )
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(self.db.scalars(stmt).all())

    def get_unread_notifications(
        self,
        user_id: int,
        organization_id: int,
    ) -> List[Notification]:

        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.status == NotificationStatus.UNREAD,
        )

        return list(self.db.scalars(stmt).all())

    def count_unread_notifications(
        self,
        user_id: int,
        organization_id: int,
    ) -> int:

        stmt = (
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.status == NotificationStatus.UNREAD,
            )
        )

        return self.db.scalar(stmt) or 0

    def mark_notification_read(
        self,
        notification: Notification,
    ) -> Notification:

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

        return result.rowcount or 0

    def get_notifications_by_entity(
        self,
        entity_type: str,
        entity_id,
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

    def delete_notification(
        self,
        notification: Notification,
    ):

        self.db.delete(notification)

    def create_notification_log(
        self,
        log: NotificationLog,
    ) -> NotificationLog:

        self.db.add(log)
        self.db.flush()

        return log

    def get_notification_logs(
        self,
        notification_id,
    ) -> List[NotificationLog]:

        stmt = select(NotificationLog).where(
            NotificationLog.notification_id == notification_id
        )

        return list(self.db.scalars(stmt).all())

    
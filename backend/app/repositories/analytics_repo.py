from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, case, desc

from app.models.user import User
from app.models.driver import Driver, DriverAvailability
from app.models.pickup import Pickup
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.audit_log import AuditLog

from app.utils.enums import (
    DriverStatus,
    DriverAvailabilityStatus,
    NotificationStatus,
)


class AnalyticsRepository:

    def __init__(self, db: Session):
        self.db = db

 

    def get_user_counts(self, organization_id: int) -> Dict:

        total_users = self.db.scalar(
            select(func.count(User.id))
            .where(User.organization_id == organization_id)
        ) or 0

        active_users = self.db.scalar(
            select(func.count(User.id))
            .where(
                User.organization_id == organization_id,
                User.is_active == True
            )
        ) or 0

        return {
            "total_users": total_users,
            "active_users": active_users,
        }

  

    def get_driver_counts(self, organization_id: int) -> Dict:

        total_drivers = self.db.scalar(
            select(func.count(Driver.id))
            .where(
                Driver.organization_id == organization_id,
                Driver.status != DriverStatus.DELETED
            )
        ) or 0

        active_drivers = self.db.scalar(
            select(func.count(Driver.id))
            .where(
                Driver.organization_id == organization_id,
                Driver.status == DriverStatus.ACTIVE
            )
        ) or 0

        available_drivers = self.db.scalar(
            select(func.count(DriverAvailability.id))
            .join(Driver)
            .where(
                Driver.organization_id == organization_id,
                DriverAvailability.status == DriverAvailabilityStatus.AVAILABLE,
                DriverAvailability.is_on_duty == True
            )
        ) or 0

        busy_drivers = self.db.scalar(
            select(func.count(DriverAvailability.id))
            .join(Driver)
            .where(
                Driver.organization_id == organization_id,
                DriverAvailability.status == DriverAvailabilityStatus.BUSY
            )
        ) or 0

        offline_drivers = self.db.scalar(
            select(func.count(DriverAvailability.id))
            .join(Driver)
            .where(
                Driver.organization_id == organization_id,
                DriverAvailability.status == DriverAvailabilityStatus.OFFLINE
            )
        ) or 0

        return {
            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
            "available_drivers": available_drivers,
            "busy_drivers": busy_drivers,
            "offline_drivers": offline_drivers,
        }


    def get_pickup_counts(self, organization_id: int) -> Dict:

        total_pickups = self.db.scalar(
            select(func.count(Pickup.id))
            .where(Pickup.organization_id == organization_id)
        ) or 0

        completed_pickups = self.db.scalar(
            select(func.count(Pickup.id))
            .where(
                Pickup.organization_id == organization_id,
                Pickup.status == "COMPLETED"
            )
        ) or 0

        cancelled_pickups = self.db.scalar(
            select(func.count(Pickup.id))
            .where(
                Pickup.organization_id == organization_id,
                Pickup.status == "CANCELLED"
            )
        ) or 0

        pending_pickups = self.db.scalar(
            select(func.count(Pickup.id))
            .where(
                Pickup.organization_id == organization_id,
                Pickup.status == "CREATED"
            )
        ) or 0

        completion_rate = (
            (completed_pickups / total_pickups) * 100
            if total_pickups > 0 else 0
        )

        return {
            "total_pickups": total_pickups,
            "completed_pickups": completed_pickups,
            "cancelled_pickups": cancelled_pickups,
            "pending_pickups": pending_pickups,
            "completion_rate": round(completion_rate, 2),
        }

   

    def get_notification_counts(self, organization_id: int) -> Dict:

        total_notifications = self.db.scalar(
            select(func.count(Notification.id))
            .where(Notification.organization_id == organization_id)
        ) or 0

        unread_notifications = self.db.scalar(
            select(func.count(Notification.id))
            .where(
                Notification.organization_id == organization_id,
                Notification.status == NotificationStatus.UNREAD
            )
        ) or 0

        read_notifications = self.db.scalar(
            select(func.count(Notification.id))
            .where(
                Notification.organization_id == organization_id,
                Notification.status == NotificationStatus.READ
            )
        ) or 0

        read_rate = (
            (read_notifications / total_notifications) * 100
            if total_notifications > 0 else 0
        )

        return {
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "read_notifications": read_notifications,
            "read_rate": round(read_rate, 2),
        }


    def get_subscription_counts(self, organization_id: int) -> Dict:

        active_subscriptions = self.db.scalar(
            select(func.count(Subscription.id))
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status == "ACTIVE"
            )
        ) or 0

        expired_subscriptions = self.db.scalar(
            select(func.count(Subscription.id))
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status == "EXPIRED"
            )
        ) or 0

        return {
            "active_subscriptions": active_subscriptions,
            "expired_subscriptions": expired_subscriptions,
        }

  

    def get_user_activity_counts(self, organization_id: int) -> Dict:

        today = datetime.utcnow().date()

        logins_today = self.db.scalar(
            select(func.count(AuditLog.id))
            .where(
                AuditLog.org_id == organization_id,
                AuditLog.action == "login",
                func.date(AuditLog.created_at) == today
            )
        ) or 0

        return {
            "logins_today": logins_today,
        }



    def get_dashboard_summary(self, organization_id: int) -> Dict:

        return {
            "users": self.get_user_counts(organization_id),
            "drivers": self.get_driver_counts(organization_id),
            "pickups": self.get_pickup_counts(organization_id),
            "notifications": self.get_notification_counts(organization_id),
            "subscriptions": self.get_subscription_counts(organization_id),
            "activity": self.get_user_activity_counts(organization_id),
        }
from typing import Dict, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.repositories.analytics_repo import AnalyticsRepository
from app.services.audit_service import AuditService


class AnalyticsService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)
        self.audit_service = AuditService(db)

   

    def get_organization_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        user_metrics = self.repo.get_user_counts(organization_id)
        driver_metrics = self.repo.get_driver_counts(organization_id)
        pickup_metrics = self.repo.get_pickup_counts(organization_id)
        subscription_metrics = self.repo.get_subscription_counts(organization_id)

        dashboard = {
            "users": user_metrics,
            "drivers": driver_metrics,
            "pickups": pickup_metrics,
            "subscriptions": subscription_metrics,
        }

        self._log_analytics_access(
            organization_id,
            requested_by,
            "organization_dashboard_viewed"
        )

        return dashboard

    

    def get_driver_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        driver_metrics = self.repo.get_driver_counts(organization_id)

        self._log_analytics_access(
            organization_id,
            requested_by,
            "driver_dashboard_viewed"
        )

        return driver_metrics

    

    def get_pickup_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        pickup_metrics = self.repo.get_pickup_counts(organization_id)

        self._log_analytics_access(
            organization_id,
            requested_by,
            "pickup_dashboard_viewed"
        )

        return pickup_metrics

    

    def get_notification_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        notification_metrics = self.repo.get_notification_counts(
            organization_id
        )

        self._log_analytics_access(
            organization_id,
            requested_by,
            "notification_dashboard_viewed"
        )

        return notification_metrics

    

    def get_user_activity_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        activity_metrics = self.repo.get_user_activity_counts(
            organization_id
        )

        self._log_analytics_access(
            organization_id,
            requested_by,
            "user_activity_dashboard_viewed"
        )

        return activity_metrics

    

    def get_subscription_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        subscription_metrics = self.repo.get_subscription_counts(
            organization_id
        )

        self._log_analytics_access(
            organization_id,
            requested_by,
            "subscription_dashboard_viewed"
        )

        return subscription_metrics


    def get_summary_dashboard(
        self,
        organization_id: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        summary = self.repo.get_dashboard_summary(
            organization_id
        )

        self._log_analytics_access(
            organization_id,
            requested_by,
            "summary_dashboard_viewed"
        )

        return summary

    

    def get_time_filtered_summary(
        self,
        organization_id: int,
        days: int,
        requested_by: Optional[int] = None,
    ) -> Dict:

        # this is extendable to repo-level time filters later
        summary = self.repo.get_dashboard_summary(
            organization_id
        )

        summary["time_range_days"] = days

        self._log_analytics_access(
            organization_id,
            requested_by,
            f"time_filtered_dashboard_{days}_days"
        )

        return summary

   

    def _log_analytics_access(
        self,
        organization_id: int,
        requested_by: Optional[int],
        action: str,
    ):

        if requested_by is None:
            return

        try:

            self.audit_service.log_action(
                user_id=requested_by,
                action=action,
                org_id=organization_id,
                meta=None,
            )

        except Exception:
            # analytics should never break dashboard if audit fails
            pass
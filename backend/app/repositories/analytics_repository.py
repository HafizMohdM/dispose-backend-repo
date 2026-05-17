from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from app.models.analytics import AnalyticsEvent, DailyMetric, PickupMetric, EventType
from app.models.sustainability import SustainabilityMetric
from datetime import date, timedelta
from typing import List, Optional, Dict, Any

class AnalyticsRepository:
    """
    Data access layer for complex analytics queries and materialized metric retrieval.
    """

    @staticmethod
    def get_daily_metrics(db: Session, org_id: int, days: int = 30) -> List[DailyMetric]:
        start_date = date.today() - timedelta(days=days)
        return db.query(DailyMetric).filter(
            and_(
                DailyMetric.organization_id == org_id,
                DailyMetric.date >= start_date
            )
        ).order_by(DailyMetric.date.asc()).all()

    @staticmethod
    def get_latest_sustainability_metrics(db: Session, org_id: int) -> Optional[SustainabilityMetric]:
        return db.query(SustainabilityMetric).filter(
            SustainabilityMetric.organization_id == org_id
        ).order_by(SustainabilityMetric.date.desc()).first()

    @staticmethod
    def get_pickup_distribution(db: Session, org_id: int, start_date: date, end_date: date) -> List[Any]:
        return db.query(
            PickupMetric.waste_type,
            func.sum(PickupMetric.pickup_count).label("count"),
            func.sum(PickupMetric.total_weight).label("weight")
        ).filter(
            and_(
                PickupMetric.organization_id == org_id,
                PickupMetric.date.between(start_date, end_date)
            )
        ).group_by(PickupMetric.waste_type).all()

    @staticmethod
    def get_event_summary(db: Session, org_id: int, event_type: EventType, days: int = 7) -> int:
        start_date = date.today() - timedelta(days=days)
        return db.query(AnalyticsEvent).filter(
            and_(
                AnalyticsEvent.organization_id == org_id,
                AnalyticsEvent.event_type == event_type,
                AnalyticsEvent.created_at >= start_date
            )
        ).count()

    @staticmethod
    def get_active_fleet_status(db: Session, org_id: int) -> Dict[str, Any]:
        """
        Aggregate current status of all drivers in the org.
        """
        # This would normally query the LiveDriverLocation table or Redis
        # For the repository, we look at the last 15 minutes of heartbeats
        from app.models.fleet import LiveDriverLocation
        from datetime import datetime, timedelta
        
        threshold = datetime.utcnow() - timedelta(minutes=15)
        active_count = db.query(LiveDriverLocation).filter(
            and_(
                LiveDriverLocation.organization_id == org_id,
                LiveDriverLocation.updated_at >= threshold
            )
        ).count()
        
        return {
            "online_drivers": active_count,
            "timestamp": datetime.utcnow()
        }

from sqlalchemy.orm import Session, joinedload
from typing import List

from app.models.pickup_exception import PickupException
from app.models.pickup_activity import PickupActivity
from app.models.notification import Notification
from app.models.route_optimization import OptimizedRoute
from app.models.pickup import Pickup

class LogisticsRepository:
    """
    High-performance repository for Operational Intelligence.
    Ensures ZERO N+1 regressions by explicitly eager loading required relationships.
    """
    
    @staticmethod
    def get_pickup_exceptions(db: Session, organization_id: int, limit: int = 100) -> List[PickupException]:
        """
        Batch query to load exceptions linked to the organization's pickups.
        """
        return db.query(PickupException).join(
            Pickup, Pickup.id == PickupException.pickup_id
        ).filter(
            Pickup.organization_id == organization_id
        ).options(
            joinedload(PickupException.pickup),
            joinedload(PickupException.reported_by),
            joinedload(PickupException.resolved_by)
        ).order_by(PickupException.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_activity_timeline(db: Session, organization_id: int, limit: int = 100) -> List[PickupActivity]:
        """
        Sequential Activity Timeline ledger.
        Explicitly loads relational tables via batch queries to prevent property loop N+1 calls.
        """
        return db.query(PickupActivity).join(
            Pickup, Pickup.id == PickupActivity.pickup_id
        ).filter(
            Pickup.organization_id == organization_id
        ).options(
            joinedload(PickupActivity.pickup),
            joinedload(PickupActivity.user)
        ).order_by(PickupActivity.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_notifications(db: Session, organization_id: int, limit: int = 100) -> List[Notification]:
        """
        Multi-tenant Notification Event ledger fetching.
        Uses explicit organization_id parsing.
        """
        return db.query(Notification).filter(
            Notification.organization_id == organization_id
        ).order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_route_plans(db: Session, organization_id: int, limit: int = 50) -> List[OptimizedRoute]:
        """
        Fetches Route Plans including their waypoints eagerly to avoid N+1 queries.
        """
        return db.query(OptimizedRoute).filter(
            OptimizedRoute.organization_id == organization_id
        ).options(
            joinedload(OptimizedRoute.waypoints)
        ).order_by(OptimizedRoute.created_at.desc()).limit(limit).all()

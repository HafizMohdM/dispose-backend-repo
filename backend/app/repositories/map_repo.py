from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.fleet import RouteSession, DriverRoute, MapEvent, LiveDriverLocation
from app.models.pickup import Pickup, PickupStatus
from typing import List, Optional

class MapRepository:
    
    @staticmethod
    def get_live_map_snapshot(db: Session, organization_id: int):
        # Fetch active vehicles
        vehicles = db.query(LiveDriverLocation).filter(
            LiveDriverLocation.organization_id == organization_id
        ).all()
        
        # Fetch pending/active pickups for map overlays
        pickups = db.query(Pickup).filter(
            and_(
                Pickup.organization_id == organization_id,
                Pickup.status.in_([PickupStatus.PENDING, PickupStatus.ASSIGNED, PickupStatus.IN_PROGRESS])
            )
        ).all()
        
        return {
            "vehicles": vehicles,
            "pickups": pickups
        }

    @staticmethod
    def get_route_by_driver(db: Session, driver_id: int) -> Optional[DriverRoute]:
        # Get the latest active route for the driver
        return db.query(DriverRoute).join(RouteSession).filter(
            and_(
                RouteSession.driver_id == driver_id,
                RouteSession.status == "active"
            )
        ).order_by(DriverRoute.created_at.desc()).first()

    @staticmethod
    def create_map_event(db: Session, event: MapEvent) -> MapEvent:
        db.add(event)
        return event

    @staticmethod
    def get_active_events(db: Session, organization_id: int) -> List[MapEvent]:
        # Return events from the last 12 hours
        from datetime import datetime, timedelta
        threshold = datetime.utcnow() - timedelta(hours=12)
        return db.query(MapEvent).filter(
            and_(
                MapEvent.organization_id == organization_id,
                MapEvent.created_at >= threshold
            )
        ).all()

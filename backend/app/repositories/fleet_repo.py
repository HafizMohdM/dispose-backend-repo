from sqlalchemy.orm import Session
from sqlalchemy import and_, update
from datetime import datetime
from app.models.fleet import GPSHistory, DriverTrackingSession, LiveDriverLocation
from typing import List, Optional

class FleetRepository:
    
    @staticmethod
    def create_gps_history(db: Session, history: GPSHistory) -> GPSHistory:
        db.add(history)
        return history

    @staticmethod
    def update_live_location(db: Session, location_data: dict):
        """
        High-performance UPSERT for live driver location.
        """
        driver_id = location_data["driver_id"]
        
        # Check if exists
        existing = db.query(LiveDriverLocation).filter(LiveDriverLocation.driver_id == driver_id).first()
        
        if existing:
            for key, value in location_data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
        else:
            new_location = LiveDriverLocation(**location_data)
            db.add(new_location)
        
        return existing or new_location

    @staticmethod
    def start_tracking_session(db: Session, driver_id: int, organization_id: int) -> DriverTrackingSession:
        # Close any existing active sessions for this driver first
        db.query(DriverTrackingSession).filter(
            and_(DriverTrackingSession.driver_id == driver_id, DriverTrackingSession.status == "active")
        ).update({"status": "completed", "ended_at": datetime.utcnow()})
        
        new_session = DriverTrackingSession(
            driver_id=driver_id,
            organization_id=organization_id,
            status="active"
        )
        db.add(new_session)
        return new_session

    @staticmethod
    def get_active_fleet(db: Session, organization_id: int) -> List[LiveDriverLocation]:
        # Only return drivers updated in the last 5 minutes (online)
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(minutes=5)
        
        return db.query(LiveDriverLocation).filter(
            and_(
                LiveDriverLocation.organization_id == organization_id,
                LiveDriverLocation.updated_at >= threshold
            )
        ).all()

    @staticmethod
    def close_stale_sessions(db: Session, timeout_minutes: int = 10):
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        # This would typically be called by a Celery task
        db.query(DriverTrackingSession).filter(
            and_(
                DriverTrackingSession.status == "active",
                DriverTrackingSession.started_at < threshold
            )
        ).update({"status": "timed_out", "ended_at": datetime.utcnow()})

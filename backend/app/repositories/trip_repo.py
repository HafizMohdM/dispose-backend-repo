from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.models.trip import Trip, TripStop

class TripRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_trip(self, trip: Trip) -> Trip:
        self.db.add(trip)
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def get_trip_by_id(self, trip_id: UUID, organization_id: int) -> Optional[Trip]:
        return self.db.query(Trip).filter(
            Trip.id == trip_id,
            Trip.organization_id == organization_id
        ).first()

    def get_trips(self, organization_id: int, skip: int = 0, limit: int = 100) -> List[Trip]:
        return self.db.query(Trip).filter(
            Trip.organization_id == organization_id
        ).offset(skip).limit(limit).all()

    def update_trip(self, trip: Trip) -> Trip:
        self.db.commit()
        self.db.refresh(trip)
        return trip

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime

from app.models.trip import Trip, TripStop, TripStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.driver import DriverAvailability
from app.utils.enums import DriverAvailabilityStatus
from app.repositories.trip_repo import TripRepository
from app.api.v1.trips.trip_schemas import TripCreate, TripStatusUpdateRequest

class TripService:
    def __init__(self, db: Session):
        self.db = db
        self.trip_repo = TripRepository(db)

    def create_trip(self, organization_id: int, trip_data: TripCreate) -> Trip:
        new_trip = Trip(
            organization_id=organization_id,
            vehicle_id=trip_data.vehicle_id,
            driver_id=trip_data.driver_id,
            status=TripStatus.PENDING
        )
        
        for stop_data in trip_data.stops:
            new_stop = TripStop(
                sequence_order=stop_data.sequence_order,
                location_name=stop_data.location_name,
                address=stop_data.address,
                latitude=stop_data.latitude,
                longitude=stop_data.longitude,
                notes=stop_data.notes
            )
            new_trip.stops.append(new_stop)

        return self.trip_repo.create_trip(new_trip)

    def get_trip(self, trip_id: UUID, organization_id: int) -> Trip:
        trip = self.trip_repo.get_trip_by_id(trip_id, organization_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found."
            )
        return trip

    def list_trips(self, organization_id: int, skip: int = 0, limit: int = 100):
        return self.trip_repo.get_trips(organization_id, skip, limit)

    def update_trip_status(self, trip_id: UUID, organization_id: int, new_status: TripStatus) -> Trip:
        trip = self.get_trip(trip_id, organization_id)

        # Enforce linear state machine
        # PENDING -> EN_ROUTE -> ACTIVE_LOADING -> COMPLETED
        valid_transitions = {
            TripStatus.PENDING: [TripStatus.EN_ROUTE, TripStatus.CANCELLED],
            TripStatus.EN_ROUTE: [TripStatus.ACTIVE_LOADING, TripStatus.PAUSED, TripStatus.CANCELLED],
            TripStatus.ACTIVE_LOADING: [TripStatus.COMPLETED, TripStatus.CANCELLED],
            TripStatus.PAUSED: [TripStatus.EN_ROUTE, TripStatus.CANCELLED],
            TripStatus.COMPLETED: [],
            TripStatus.CANCELLED: []
        }

        if new_status not in valid_transitions.get(trip.status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trip status transition from {trip.status.value} to {new_status.value}."
            )

        try:
            with self.db.begin_nested():
                trip.status = new_status
                
                if new_status == TripStatus.EN_ROUTE:
                    trip.start_time = datetime.utcnow()
                    
                    # Cascade State Management: When marked STARTED (EN_ROUTE)
                    vehicle = self.db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
                    if vehicle:
                        vehicle.status = VehicleStatus.ACTIVE
                        
                    driver_availability = self.db.query(DriverAvailability).filter(
                        DriverAvailability.driver_id == trip.driver_id
                    ).first()
                    
                    if driver_availability:
                        driver_availability.status = DriverAvailabilityStatus.BUSY
                        driver_availability.is_on_duty = True
                    else:
                        new_avail = DriverAvailability(
                            driver_id=trip.driver_id,
                            status=DriverAvailabilityStatus.BUSY,
                            is_on_duty=True
                        )
                        self.db.add(new_avail)

                elif new_status == TripStatus.COMPLETED:
                    trip.end_time = datetime.utcnow()
                    
                    # Cascade State Management: Revert vehicle and driver state
                    vehicle = self.db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
                    if vehicle:
                        vehicle.status = VehicleStatus.INACTIVE
                        
                    driver_availability = self.db.query(DriverAvailability).filter(
                        DriverAvailability.driver_id == trip.driver_id
                    ).first()
                    if driver_availability:
                        driver_availability.status = DriverAvailabilityStatus.AVAILABLE
            
            self.db.commit()
            self.db.refresh(trip)
            return trip
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update trip status: {str(e)}"
            )

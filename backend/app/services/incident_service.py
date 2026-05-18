from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.trip import Trip, TripStatus
from app.repositories.incident_repo import IncidentRepository

class IncidentService:
    def __init__(self, db: Session):
        self.db = db
        self.incident_repo = IncidentRepository(db)

    def report_incident(
        self,
        organization_id: int,
        incident_type: str,
        description: str,
        severity: IncidentSeverity,
        reported_by: int,
        vehicle_id: Optional[UUID] = None,
        driver_id: Optional[UUID] = None,
        trip_id: Optional[UUID] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Incident:
        
        new_incident = Incident(
            organization_id=organization_id,
            incident_type=incident_type,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            trip_id=trip_id,
            latitude=latitude,
            longitude=longitude,
            reported_by=reported_by
        )

        try:
            with self.db.begin_nested():
                self.db.add(new_incident)
                self.db.flush() # get new_incident.id
                
                # Cascading State Changes:
                # When an accident or engine failure is reported,
                # Vehicle.status -> MAINTENANCE
                # active Trip -> CANCELLED
                if incident_type in ["ACCIDENT", "ENGINE_FAILURE"] and vehicle_id:
                    vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
                    if vehicle:
                        vehicle.status = VehicleStatus.MAINTENANCE
                        
                    # Find any active trip for this vehicle
                    active_trips = self.db.query(Trip).filter(
                        Trip.vehicle_id == vehicle_id,
                        Trip.status.in_([TripStatus.PENDING, TripStatus.EN_ROUTE, TripStatus.ACTIVE_LOADING, TripStatus.PAUSED])
                    ).all()
                    
                    for trip in active_trips:
                        trip.status = TripStatus.CANCELLED
                        trip.updated_at = datetime.utcnow()
                        
            self.db.commit()
            self.db.refresh(new_incident)
            return new_incident
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to report incident: {str(e)}"
            )

    def get_incident(self, incident_id: UUID, organization_id: int) -> Incident:
        incident = self.incident_repo.get_by_id(incident_id, organization_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found."
            )
        return incident

    def list_incidents(self, organization_id: int, skip: int = 0, limit: int = 50) -> List[Incident]:
        return self.incident_repo.get_all(organization_id, skip, limit)

    def resolve_incident(self, incident_id: UUID, organization_id: int, resolved_by: int, resolution_notes: str) -> Incident:
        incident = self.get_incident(incident_id, organization_id)
        
        try:
            with self.db.begin_nested():
                incident.status = IncidentStatus.RESOLVED
                incident.resolved_by = resolved_by
                incident.resolution_notes = resolution_notes
                incident.resolved_at = datetime.utcnow()
                
                # We could potentially revert Vehicle back to INACTIVE here if no other open incidents exist,
                # but it's usually better for Fleet Managers to manually mark it active after an inspection.
                # So we won't automatically undo MAINTENANCE status here.
                
            self.db.commit()
            self.db.refresh(incident)
            return incident
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resolve incident: {str(e)}"
            )

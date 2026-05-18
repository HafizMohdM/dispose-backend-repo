from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.models.incident import Incident, IncidentStatus

class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, incident: Incident) -> Incident:
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def get_by_id(self, incident_id: UUID, organization_id: int) -> Optional[Incident]:
        return self.db.query(Incident).filter(
            Incident.id == incident_id,
            Incident.organization_id == organization_id
        ).first()

    def get_all(self, organization_id: int, skip: int = 0, limit: int = 50) -> List[Incident]:
        return self.db.query(Incident).filter(
            Incident.organization_id == organization_id
        ).order_by(Incident.reported_at.desc()).offset(skip).limit(limit).all()

    def get_open_incidents_by_vehicle(self, vehicle_id: UUID) -> List[Incident]:
        return self.db.query(Incident).filter(
            Incident.vehicle_id == vehicle_id,
            Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS])
        ).all()

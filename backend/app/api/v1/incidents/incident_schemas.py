from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.incident import IncidentSeverity, IncidentStatus

class IncidentCreate(BaseModel):
    incident_type: str = Field(..., max_length=100)
    description: str
    severity: IncidentSeverity
    vehicle_id: Optional[UUID] = None
    driver_id: Optional[UUID] = None
    trip_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class IncidentResolveRequest(BaseModel):
    resolution_notes: str

class IncidentResponse(BaseModel):
    id: UUID
    organization_id: int
    incident_type: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    vehicle_id: Optional[UUID]
    driver_id: Optional[UUID]
    trip_id: Optional[UUID]
    latitude: Optional[float]
    longitude: Optional[float]
    reported_by: Optional[int]
    resolved_by: Optional[int]
    resolution_notes: Optional[str]
    reported_at: datetime
    resolved_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

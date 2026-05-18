from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.models.trip import TripStatus, TripStopStatus

class TripStopBase(BaseModel):
    sequence_order: int
    location_name: str
    address: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    notes: Optional[str] = None

class TripStopCreate(TripStopBase):
    pass

class TripStopResponse(TripStopBase):
    id: UUID
    trip_id: UUID
    status: TripStopStatus
    arrival_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class TripBase(BaseModel):
    vehicle_id: UUID
    driver_id: UUID

class TripCreate(TripBase):
    stops: List[TripStopCreate] = Field(..., min_length=1)

class TripResponse(TripBase):
    id: UUID
    organization_id: int
    status: TripStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    stops: List[TripStopResponse] = []

    class Config:
        from_attributes = True

class TripStatusUpdateRequest(BaseModel):
    status: TripStatus

from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class LocationStreamRequest(BaseModel):
    latitude: float
    longitude: float
    speed: Optional[float] = 0.0
    heading: Optional[float] = 0.0
    accuracy: Optional[float] = 0.0

class LiveDriverResponse(BaseModel):
    driver_id: int
    latitude: float
    longitude: float
    speed: float
    heading: float
    updated_at: datetime

    class Config:
        from_attributes = True

class FleetLiveResponse(BaseModel):
    drivers: List[LiveDriverResponse]
    total_online: int

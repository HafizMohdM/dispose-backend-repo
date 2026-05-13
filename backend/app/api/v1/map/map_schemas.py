from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Any

class MapVehicleResponse(BaseModel):
    driver_id: int
    latitude: float
    longitude: float
    speed: float
    updated_at: datetime

class MapPickupResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    status: str
    waste_type: str

class LiveMapResponse(BaseModel):
    vehicles: List[MapVehicleResponse]
    pickups: List[MapPickupResponse]
    timestamp: datetime

class RouteResponse(BaseModel):
    route_session_id: int
    polyline_data: str
    distance_km: float
    estimated_duration_min: int

class MapEventCreate(BaseModel):
    event_type: str
    latitude: float
    longitude: float
    metadata: Optional[dict] = None

class MapEventResponse(BaseModel):
    id: int
    event_type: str
    latitude: float
    longitude: float
    metadata_json: Optional[str]
    created_at: datetime

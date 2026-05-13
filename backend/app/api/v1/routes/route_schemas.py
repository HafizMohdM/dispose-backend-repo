from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class RouteOptimizeRequest(BaseModel):
    vehicle_id: int
    pickup_ids: List[int]

class WaypointResponse(BaseModel):
    id: int
    stop_number: int
    waypoint_type: str
    latitude: float
    longitude: float
    is_completed: bool

    class Config:
        from_attributes = True

class OptimizedRouteResponse(BaseModel):
    id: int
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    status: str
    total_distance_km: float
    estimated_duration_min: int
    waypoints: List[WaypointResponse]
    created_at: datetime

    class Config:
        from_attributes = True

class RouteAssignRequest(BaseModel):
    driver_id: int

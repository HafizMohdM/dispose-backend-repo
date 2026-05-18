from pydantic import BaseModel, UUID4
from typing import List, Optional
from datetime import datetime

# --- Pickup Exceptions ---
class PickupExceptionResponse(BaseModel):
    id: int
    pickup_id: int
    exception_type: str
    notes: Optional[str]
    reported_by_id: Optional[int]
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Activity Timeline ---
class ActivityTimelineResponse(BaseModel):
    id: int
    pickup_id: int
    user_id: Optional[int]
    activity_type: str
    description: str
    notes: Optional[str]
    metadata_payload: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Notifications ---
class NotificationEventResponse(BaseModel):
    id: UUID4
    organization_id: int
    user_id: int
    title: str
    message: str
    type: str
    status: str
    entity_type: Optional[str]
    entity_id: Optional[UUID4]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Route Optimization ---
class LogisticsRouteOptimizeRequest(BaseModel):
    pickup_ids: List[int]
    vehicle_id: Optional[int]
    depot_latitude: Optional[float]
    depot_longitude: Optional[float]

class LogisticsRouteWaypointResponse(BaseModel):
    id: int
    stop_number: int
    waypoint_type: str
    reference_id: Optional[int]
    latitude: float
    longitude: float
    is_completed: bool

    class Config:
        from_attributes = True

class LogisticsRoutePlanResponse(BaseModel):
    id: int
    organization_id: int
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    status: str
    total_distance_km: float
    estimated_duration_min: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    waypoints: List[LogisticsRouteWaypointResponse] = []

    class Config:
        from_attributes = True

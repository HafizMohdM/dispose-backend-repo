from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RouteOptimizeRequest(BaseModel):
    pickup_ids: List[int] = Field(..., min_items=1, description="List of pickup IDs to optimize")
    vehicle_id: Optional[int] = Field(None, description="Vehicle to be used for this route")
    depot_latitude: Optional[float] = Field(None, description="Starting point latitude (depot/warehouse)")
    depot_longitude: Optional[float] = Field(None, description="Starting point longitude")
    return_to_depot: bool = Field(True, description="Whether driver should return to depot after last pickup")

class RouteWaypointResponse(BaseModel):
    id: int
    stop_number: int
    waypoint_type: str
    reference_id: Optional[int]
    latitude: float
    longitude: float
    is_completed: bool
    arrival_time: Optional[datetime] = None

    model_config = {"from_attributes": True}

class OptimizedRouteResponse(BaseModel):
    id: int
    organization_id: int
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    status: str
    total_distance_km: float
    estimated_duration_min: int
    optimized_polyline: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    waypoints: List[RouteWaypointResponse]
    optimization_score: Optional[float] = None  # 0-100 score

    model_config = {"from_attributes": True}

class RouteAssignRequest(BaseModel):
    driver_id: int
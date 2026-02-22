from pydantic import BaseModel, Field, conint, confloat
from typing import Optional, List
from datetime import datetime
from app.models.pickup import WasteType, PickupStatus
from app.models.pickup_assignment import AssignmentStatus

class PickupCreateRequest(BaseModel):
    waste_type: WasteType
    waste_weight: float = Field(..., gt=0, description="Weight of the waste in kg (must be positive)")
    address: str = Field(..., max_length=500, description="Full address for the pickup")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    scheduled_at: Optional[datetime] = Field(None, description="Optional scheduled time for pickup")

class PickupResponse(BaseModel):
    id: int
    organization_id: int
    subscription_id: Optional[int] = None
    waste_type: WasteType
    waste_weight: float
    address: str
    latitude: float
    longitude: float
    status: PickupStatus
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PickupUpdateStatusRequest(BaseModel):
    status: PickupStatus
    
class PickupAssignmentResponse(BaseModel):
    id: int
    pickup_id: int
    driver_id: int
    status: AssignmentStatus
    assigned_at: datetime
    
    model_config = {"from_attributes": True}

class PickupListResponse(BaseModel):
    pickups: List[PickupResponse]
    total: int

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.pickup_activity import ActivityType

class PickupActivityBase(BaseModel):
    notes: str

class PickupActivityCreateRequest(PickupActivityBase):
    pass

class PickupActivityResponse(BaseModel):
    id: int
    pickup_id: int
    user_id: Optional[int]
    activity_type: ActivityType
    description: str
    notes: Optional[str]
    metadata_payload: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class PickupTimelineResponse(BaseModel):
    pickup_id: int
    total_events: int
    timeline: List[PickupActivityResponse]
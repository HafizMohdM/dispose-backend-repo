from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.models.recurring_pickup import RecurringFrequency

class RecurringPickupCreateRequest(BaseModel):
    waste_type: str = Field(..., description="Type of waste")
    waste_weight: float = Field(..., description="Estimated weight of waste")
    address: str = Field(..., description="Pickup address")
    latitude: float = Field(..., description="Latitude of pickup location")
    longitude: float = Field(..., description="Longitude of pickup location")
    frequency: RecurringFrequency = Field(..., description="Frequency of the pickup (DAILY, WEEKLY, MONTHLY)")
    next_run_at: datetime = Field(..., description="Next scheduled run datetime")

class RecurringPickupResponse(BaseModel):
    id: int
    organization_id: int
    waste_type: str
    waste_weight: float
    address: str
    latitude: float
    longitude: float
    frequency: RecurringFrequency
    next_run_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

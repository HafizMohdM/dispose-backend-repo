from pydantic import BaseModel, Field, conint, confloat, validator
from typing import Optional
from datetime import datetime, timezone

class PickupCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=5, max_length=500, description="Reason for cancelling the pickup")

class PickupRescheduleRequest(BaseModel):
    new_scheduled_at: datetime = Field(..., description="The new date and time for the pickup")
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for rescheduling")

    @validator("new_scheduled_at")
    def validate_future_date(cls, v):
        # Allow naive datetimes to be treated as UTC, or compare aware against aware
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("new_scheduled_at must be in the future")
        return v

class PickupRejectRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Reason the driver is rejecting the assignment")

class PickupCompleteRequest(BaseModel):
    actual_weight: float = Field(..., ge=0, description="The actual measured weight of the collected waste in kg")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the completed pickup")

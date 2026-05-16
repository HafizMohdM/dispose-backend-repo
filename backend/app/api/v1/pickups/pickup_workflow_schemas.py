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


# ==================== BULK OPERATION SCHEMAS ====================

from typing import List, Dict, Any

class BulkAssignRequest(BaseModel):
    """Dispatcher selects multiple PENDING pickups and assigns them to a single driver."""
    pickup_ids: List[int] = Field(..., min_length=1, max_length=100, description="List of pickup IDs to assign")
    driver_id: int = Field(..., description="The driver ID to assign all pickups to")

class BulkCancelRequest(BaseModel):
    """Dispatcher selects multiple pickups and cancels them in one atomic operation."""
    pickup_ids: List[int] = Field(..., min_length=1, max_length=100, description="List of pickup IDs to cancel")
    cancellation_reason: str = Field(..., min_length=5, max_length=500, description="Reason for bulk cancellation")

class BulkRescheduleRequest(BaseModel):
    """Dispatcher selects multiple pickups and reschedules them to a new date/time."""
    pickup_ids: List[int] = Field(..., min_length=1, max_length=100, description="List of pickup IDs to reschedule")
    new_scheduled_at: datetime = Field(..., description="The new date and time for all selected pickups")
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for bulk rescheduling")

    @validator("new_scheduled_at")
    def validate_future_date(cls, v):
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("new_scheduled_at must be in the future")
        return v

class BulkOperationResponse(BaseModel):
    """Standardized response envelope for all bulk dispatcher operations."""
    operation: str = Field(..., description="The bulk operation that was performed")
    affected_count: int = Field(..., description="Number of pickups successfully modified")
    affected_pickup_ids: List[int] = Field(..., description="List of pickup IDs that were modified")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional operation-specific metadata")

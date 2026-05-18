from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.pickup_exception import ExceptionType

class PickupExceptionCreateRequest(BaseModel):
    exception_type: ExceptionType = Field(..., description="Type of exception")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional details about the exception")

class PickupExceptionResponse(BaseModel):
    id: int
    pickup_id: int
    exception_type: ExceptionType
    notes: Optional[str]
    resolved: bool
    reported_by_id: Optional[int]
    resolved_at: Optional[datetime]
    resolved_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PickupExceptionListResponse(BaseModel):
    exceptions: List[PickupExceptionResponse]
    total: int


class PickupExceptionStatsResponse(BaseModel):
    total_exceptions: int
    resolved_count: int
    unresolved_count: int
    resolution_rate: float
    type_breakdown: dict
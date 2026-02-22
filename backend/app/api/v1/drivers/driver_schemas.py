from datetime import datetime
from typing import Optional,List
from uuid import UUID
from pydantic import BaseModel,Field,EmailStr

from app.utils.enums import DriverStatus,DriverAvailabilityStatus


class DriverCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=100)
    license_expiry: Optional[datetime] = None
    notes: Optional[str] =None

class DriverUpdateRequest(BaseModel):

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=100)
    license_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[DriverStatus] = None

class DriverResponse(BaseModel):

    id: UUID
    organization_id: UUID
    name: str
    mobile: str
    email: Optional[str]
    license_number: Optional[str]
    license_expiry: Optional[datetime]
    status: DriverStatus
    created_by: UUID
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class DriverAvailabilityUpdateRequest(BaseModel):
    status:DriverAvailabilityStatus
    is_on_duty:bool

class DriverLocationUpdateRequest(BaseModel):
    latitude:float
    longitude:float
    accuracy:Optional[float] = None


class DriverListResponse(BaseModel):
    drivers: List[DriverResponse]
    total: int


from datetime import datetime
from typing import Optional,List
from uuid import UUID
from pydantic import BaseModel,Field,EmailStr

from app.utils.enums import DriverStatus, DriverAvailabilityStatus
from app.models.driver_operations import ShiftStatus, DocumentVerificationStatus


class DriverCreateRequest(BaseModel):
    organization_id: Optional[int] = None
    name: str = Field(..., min_length=3, max_length=100)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=100)
    license_expiry: Optional[datetime] = None
    notes: Optional[str] =None

class DriverUpdateRequest(BaseModel):
    organization_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=100)
    license_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[DriverStatus] = None

class DriverResponse(BaseModel):

    id: UUID
    organization_id: int
    name: str
    mobile: str
    email: Optional[str]
    license_number: Optional[str]
    license_expiry: Optional[datetime]
    status: DriverStatus
    active_workload: Optional[int] = 0
    distance_meters: Optional[float] = None
    created_by: int
    updated_by: Optional[int]
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

class DriverShiftResponse(BaseModel):
    id: UUID
    driver_id: UUID
    organization_id: int
    clock_in_time: datetime
    clock_out_time: Optional[datetime]
    status: ShiftStatus

    class Config:
        from_attributes = True

class DriverDocumentCreate(BaseModel):
    document_type: str = Field(..., max_length=100)
    file_url: str = Field(..., max_length=500)

class DriverDocumentResponse(BaseModel):
    id: UUID
    driver_id: UUID
    document_type: str
    file_url: str
    verification_status: DocumentVerificationStatus
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class DocumentVerifyRequest(BaseModel):
    status: DocumentVerificationStatus
    rejection_reason: Optional[str] = None


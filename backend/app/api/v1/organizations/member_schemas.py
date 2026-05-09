from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.organization_member import MembershipStatus

class MemberCreate(BaseModel):
    email: EmailStr
    role_id: int

class MemberUpdate(BaseModel):
    role_id: Optional[int] = None
    status: Optional[MembershipStatus] = None

class MemberResponse(BaseModel):
    id: UUID
    organization_id: int
    user_id: int
    role_id: int
    status: MembershipStatus
    joined_at: Optional[datetime] = None
    created_at: datetime
    
    # Extra fields for the API response view
    email: Optional[str] = None
    role_name: Optional[str] = None

    class Config:
        from_attributes = True

from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models.invitation import InvitationStatus

class InviteRecord(BaseModel):
    email: EmailStr
    role: str

class DirectUserCreate(BaseModel):
    mobile: str
    email: EmailStr
    role: str
    is_active: bool = True

class BulkInviteRequest(BaseModel):
    invites: List[InviteRecord]

class InvitationResponse(BaseModel):
    id: int
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class CursorPaginationParams(BaseModel):
    limit: int = 20
    last_seen_id: Optional[int] = None
    search: Optional[str] = None

class UserListCursorResponse(BaseModel):
    users: List[dict]
    next_cursor: Optional[int]
    has_more: bool

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    org_id: Optional[int] = None
    user_id: int
    action: str
    meta: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

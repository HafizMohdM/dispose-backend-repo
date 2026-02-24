from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class SystemSettingResponse(BaseModel):
    id: UUID
    key: str
    value: str
    organization_id: int | None
    is_global: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SystemSettingUpdateRequest(BaseModel):
    key:str
    value: str
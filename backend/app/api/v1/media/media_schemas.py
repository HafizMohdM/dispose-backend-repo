from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class MediaResponse(BaseModel):
    id: UUID
    organization_id: int
    uploaded_by: Optional[int] = None
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

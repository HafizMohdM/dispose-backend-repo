from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

from app.utils.enums import NotificationStatus,NotificationType


class NotificationResponse(BaseModel):
    id:UUID
    organization_id:int
    user_id:int
    title:str
    message:str
    type:NotificationType
    status:NotificationStatus
    entity_type:Optional[str]
    entity_id:Optional[UUID]
    created_at:datetime
    read_at:Optional[datetime]

    class config:
        from_attributes =True

class NotificationReadResponse(BaseModel):
    success:bool
    notification_id: UUID

class NotificationReadAllResponse(BaseModel):
    success:bool
    count:int

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
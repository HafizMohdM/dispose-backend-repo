from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

from app.utils.enums import NotificationStatus, NotificationType, NotificationSeverity, NotificationCategory


class NotificationResponse(BaseModel):
    id: UUID
    organization_id: int
    user_id: int
    title: str
    message: str
    type: NotificationType
    status: NotificationStatus
    severity: NotificationSeverity
    category: NotificationCategory
    source_service: Optional[str] = None
    archived: bool
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationReadResponse(BaseModel):
    success: bool
    notification_id: UUID

class NotificationReadAllResponse(BaseModel):
    success: bool
    count: int

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int

class NotificationPreferenceResponse(BaseModel):
    id: UUID
    user_id: int
    organization_id: int
    category: NotificationCategory
    in_app_enabled: bool
    email_enabled: bool
    push_enabled: bool

    class Config:
        from_attributes = True

class NotificationPreferenceUpdate(BaseModel):
    category: NotificationCategory
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None


class DeliveryLogResponse(BaseModel):
    id: UUID
    notification_id: UUID
    channel: str
    delivery_status: str
    error_message: Optional[str] = None
    provider: Optional[str] = None
    retry_count: int = 0
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeliverySummaryResponse(BaseModel):
    summary: dict


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMetricsResponse(BaseModel):
    total_notifications: int
    unread_count: int
    archived_count: int
    read_rate: float
    category_breakdown: dict
    severity_breakdown: dict


class TestNotificationRequest(BaseModel):
    title: str
    message: str
    severity: NotificationSeverity
    category: NotificationCategory
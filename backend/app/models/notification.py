import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.base import Base
from app.utils.enums import NotificationType, NotificationStatus, NotificationSeverity, NotificationCategory, DeliveryChannel, DeliveryStatus


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    type = Column(
        Enum(NotificationType),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.UNREAD,
        index=True,
    )

    entity_type = Column(
        String(50),
        nullable=True,
    )

    entity_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    read_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    severity = Column(
        Enum(NotificationSeverity),
        nullable=False,
        default=NotificationSeverity.INFO,
        index=True,
    )

    category = Column(
        Enum(NotificationCategory),
        nullable=False,
        default=NotificationCategory.SYSTEM,
        index=True,
    )

    source_service = Column(
        String(50),
        nullable=True,
        index=True,
    )

    archived = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )


class NotificationDeliveryLog(Base):
    __tablename__ = "notification_delivery_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel = Column(
        Enum(DeliveryChannel),
        nullable=False,
        index=True,
    )

    delivery_status = Column(
        Enum(DeliveryStatus),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    provider = Column(
        String(50),
        nullable=True,
    )

    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category = Column(
        Enum(NotificationCategory),
        nullable=False,
        index=True,
    )

    in_app_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    email_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    push_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Composite unique constraint to prevent duplicate preferences per category
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category_preference"),
    )



import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.base import Base
from app.utils.enums import NotificationType, NotificationStatus


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


class NotificationLog(Base):
    __tablename__ = "notification_logs"

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

    delivery_status = Column(
        String(50),
        nullable=False,
    )

    delivery_channel = Column(
        String(50),
        nullable=False,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


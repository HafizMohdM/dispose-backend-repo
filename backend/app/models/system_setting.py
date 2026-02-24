import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    key = Column(
        String(255),
        nullable = False,
        index=True,
    )

    value = Column(
        Text,
        nullable = False,
    )

    value_type = Column(
        String(50),
        nullable= False,
        default="string",
    )

    is_global = Column(
        Boolean,
        nullable = False,
        default = False,
    )

    created_at = Column(
        DateTime(timezone= True),
        server_default = func.now(),
    )

    updated_at = Column(
        DateTime(timezone= True),
        server_default = func.now(),
        onupdate = func.now(),
    )

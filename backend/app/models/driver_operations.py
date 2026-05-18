import uuid
import enum
from sqlalchemy import Column, String, DateTime, Enum, Integer, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

class ShiftStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class DriverShift(Base):
    __tablename__ = "driver_shifts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    clock_in_time = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    clock_out_time = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(
        Enum(ShiftStatus, native_enum=False),
        nullable=False,
        default=ShiftStatus.ACTIVE,
        index=True
    )

class DocumentVerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class DriverDocument(Base):
    __tablename__ = "driver_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type = Column(String(100), nullable=False)  # e.g. "LICENSE", "BACKGROUND_CHECK"
    file_url = Column(String(500), nullable=False)
    
    verification_status = Column(
        Enum(DocumentVerificationStatus, native_enum=False),
        nullable=False,
        default=DocumentVerificationStatus.PENDING,
        index=True
    )
    
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

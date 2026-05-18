import uuid
import enum
from sqlalchemy import Column, String, DateTime, Enum, Integer, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Associated entities
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True)
    
    incident_type = Column(String(100), nullable=False) # ACCIDENT, ENGINE_FAILURE, DELAY, etc.
    description = Column(String, nullable=False)
    
    severity = Column(
        Enum(IncidentSeverity, native_enum=False),
        nullable=False,
        default=IncidentSeverity.MEDIUM,
        index=True
    )
    
    status = Column(
        Enum(IncidentStatus, native_enum=False),
        nullable=False,
        default=IncidentStatus.OPEN,
        index=True
    )
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    reported_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes = Column(String, nullable=True)
    
    reported_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

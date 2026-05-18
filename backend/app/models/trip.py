import uuid
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.models.base import Base

class TripStatus(str, enum.Enum):
    PENDING = "PENDING"
    EN_ROUTE = "EN_ROUTE"
    ACTIVE_LOADING = "ACTIVE_LOADING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    status = Column(
        Enum(TripStatus, native_enum=False),
        nullable=False,
        default=TripStatus.PENDING,
        index=True,
    )
    
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    stops = relationship("TripStop", back_populates="trip", order_by="TripStop.sequence_order", cascade="all, delete-orphan")


class TripStopStatus(str, enum.Enum):
    PENDING = "PENDING"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class TripStop(Base):
    __tablename__ = "trip_stops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sequence_order = Column(Integer, nullable=False)
    location_name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    status = Column(
        Enum(TripStopStatus, native_enum=False),
        nullable=False,
        default=TripStopStatus.PENDING,
        index=True,
    )
    
    arrival_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    
    notes = Column(String, nullable=True)

    trip = relationship("Trip", back_populates="stops")

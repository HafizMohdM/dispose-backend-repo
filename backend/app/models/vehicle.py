import uuid
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.models.base import Base

class VehicleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DELETED = "DELETED"

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    registration_number = Column(String, unique=True, index=True, nullable=False)
    vehicle_type = Column(String, nullable=False) # Truck, Van, Loader
    fuel_type = Column(String, nullable=True) # Diesel, EV, Petrol, CNG
    capacity_kg = Column(Float, default=0.0)
    
    status = Column(
        Enum(VehicleStatus, native_enum=False),
        nullable=False,
        default=VehicleStatus.INACTIVE,
        index=True,
    )
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = relationship("VehicleAssignment", back_populates="vehicle")
    maintenances = relationship("VehicleMaintenance", back_populates="vehicle")


class VehicleAssignment(Base):
    __tablename__ = "vehicle_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unassigned_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    vehicle = relationship("Vehicle", back_populates="assignments")

class MaintenanceStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class VehicleMaintenance(Base):
    __tablename__ = "vehicle_maintenance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    description = Column(String, nullable=False)
    cost = Column(Float, nullable=True)
    
    status = Column(
        Enum(MaintenanceStatus, native_enum=False),
        nullable=False,
        default=MaintenanceStatus.SCHEDULED,
        index=True,
    )
    
    scheduled_date = Column(DateTime, nullable=False)
    completed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="maintenances")


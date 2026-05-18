from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
from datetime import datetime
import enum

class VehicleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"

class MaintenanceStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("organization_id", "vin", name="uix_org_vehicle_vin"),
        UniqueConstraint("organization_id", "registration_number", name="uix_org_vehicle_registration"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    vin = Column(String(255), nullable=True)
    registration_number = Column(String(100), nullable=True)
    
    # Types: TRUCK, VAN, BIKE, etc.
    type = Column(String(50), nullable=False, default="VAN", index=True)
    
    # Status: ACTIVE, IN_MAINTENANCE, DECOMMISSIONED
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)
    
    last_telemetry_at = Column(DateTime, nullable=True)
    
    # Relationships
    assignments = relationship("VehicleAssignment", back_populates="vehicle", cascade="all, delete-orphan")
    maintenances = relationship("VehicleMaintenance", back_populates="vehicle", cascade="all, delete-orphan")

class VehicleAssignment(Base, TimestampMixin):
    """
    Stateful association mapping drivers to high-concurrency vehicles.
    """
    __tablename__ = "vehicle_assignments"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unassigned_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)

    vehicle = relationship("Vehicle", back_populates="assignments")

class VehicleMaintenance(Base, TimestampMixin):
    """
    Tracks maintenance schedules and logs for fleet vehicles.
    """
    __tablename__ = "vehicle_maintenance"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")

    vehicle = relationship("Vehicle", back_populates="maintenances")

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin

class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    registration_number = Column(String, unique=True, index=True, nullable=False)
    vehicle_type = Column(String, nullable=False) # Truck, Van, Loader
    fuel_type = Column(String, nullable=True) # Diesel, EV, Petrol, CNG
    capacity_kg = Column(Float, default=0.0)
    status = Column(String, default="active") # active, maintenance, inactive
    created_at = Column(DateTime, default=datetime.utcnow)

    assignments = relationship("VehicleAssignment", back_populates="vehicle")
    health = relationship("VehicleHealth", back_populates="vehicle", uselist=False)

class VehicleAssignment(Base):
    __tablename__ = "vehicle_assignments"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    unassigned_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    vehicle = relationship("Vehicle", back_populates="assignments")

class VehicleHealth(Base):
    __tablename__ = "vehicle_health"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), unique=True, nullable=False)
    engine_status = Column(String, default="ok")
    battery_health = Column(Integer, default=100) # Percentage
    fuel_level = Column(Integer, default=100) # Percentage
    tire_pressure = Column(String, default="normal")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="health")

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    maintenance_type = Column(String, nullable=False) # Service, Repair, Inspection
    notes = Column(String, nullable=True)
    maintenance_date = Column(DateTime, default=datetime.utcnow)
    next_due_date = Column(DateTime, nullable=True)
    cost = Column(Float, default=0.0)

import uuid
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.models.base import Base

class VehicleTelemetry(Base):
    """
    High-throughput isolated table for vehicle telemetry.
    Separated from the main Vehicle model to prevent transaction lock contention.
    """
    __tablename__ = "vehicle_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    speed_kmh = Column(Float, nullable=False, default=0.0)
    fuel_level_percentage = Column(Float, nullable=False, default=0.0)
    battery_voltage = Column(Float, nullable=False, default=0.0)
    ignition_state = Column(Boolean, nullable=False, default=False)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_vehicle_telemetry_org_vehicle_time", "organization_id", "vehicle_id", "timestamp"),
    )

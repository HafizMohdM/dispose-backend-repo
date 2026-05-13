from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin

class IOTDevice(Base, TimestampMixin):
    __tablename__ = "iot_devices"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    device_identifier = Column(String, unique=True, index=True, nullable=False) # UUID or Serial
    device_type = Column(String, nullable=False) # GPS-Tracker, OBD-Scanner, Multi-Sensor
    firmware_version = Column(String, nullable=True)
    status = Column(String, default="active") # active, inactive, maintenance
    created_at = Column(DateTime, default=datetime.utcnow)

class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    event_type = Column(String, nullable=False) # location, diagnostic, health, alert
    telemetry_data = Column(JSON, nullable=False) # Raw sensor data payload
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_telemetry_vehicle_time", "vehicle_id", "created_at"),
    )

class SensorStream(Base):
    __tablename__ = "sensor_streams"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)
    sensor_type = Column(String, nullable=False) # temperature, fuel, battery, rpm
    sensor_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_sensor_stream_device_type", "device_id", "sensor_type", "recorded_at"),
    )

class VehicleDiagnostic(Base):
    __tablename__ = "vehicle_diagnostics"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    engine_health = Column(String, default="ok")
    battery_status = Column(String, default="good")
    fuel_level = Column(Integer, default=100)
    temperature = Column(Float, nullable=True)
    diagnostic_code = Column(String, nullable=True) # OBD-II codes (e.g., P0123)
    created_at = Column(DateTime, default=datetime.utcnow)

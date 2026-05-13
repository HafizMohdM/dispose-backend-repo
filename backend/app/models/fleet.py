from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin

class GPSHistory(Base, TimestampMixin):
    __tablename__ = "gps_history"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, default=0.0)
    heading = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for fast historical queries
    __table_args__ = (
        Index("ix_gps_history_driver_org_time", "driver_id", "organization_id", "recorded_at"),
    )

class DriverTrackingSession(Base):
    __tablename__ = "driver_tracking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, default="active") # active, completed, timed_out

class LiveDriverLocation(Base):
    __tablename__ = "live_driver_locations"

    # We use driver_id as primary key to ensure one row per driver
    driver_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, default=0.0)
    heading = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Performance index for live map fetching
    __table_args__ = (
        Index("ix_live_location_org", "organization_id"),
    )

class RouteSession(Base):
    __tablename__ = "route_sessions"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    status = Column(String, default="active") # active, completed, cancelled
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class DriverRoute(Base):
    __tablename__ = "driver_routes"

    id = Column(Integer, primary_key=True, index=True)
    route_session_id = Column(Integer, ForeignKey("route_sessions.id"), nullable=False)
    polyline_data = Column(String, nullable=False) # Encoded polyline string
    distance_km = Column(Float, default=0.0)
    estimated_duration_min = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class MapEvent(Base):
    __tablename__ = "map_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    event_type = Column(String, nullable=False) # alert, traffic, breakdown, delay
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    metadata_json = Column(String, nullable=True) # JSON details
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_map_events_org_type", "organization_id", "event_type"),
    )

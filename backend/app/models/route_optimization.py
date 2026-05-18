from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin

from sqlalchemy.dialects.postgresql import UUID

class OptimizedRoute(Base, TimestampMixin):
    __tablename__ = "optimized_routes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    status = Column(String, default="draft") # draft, assigned, active, completed, cancelled
    total_distance_km = Column(Float, default=0.0)
    estimated_duration_min = Column(Integer, default=0)
    optimized_polyline = Column(String, nullable=True) # Encoded polyline for the entire route
    
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    waypoints = relationship("RouteWaypoint", back_populates="optimized_route", cascade="all, delete-orphan")

class RouteWaypoint(Base):
    __tablename__ = "route_waypoints"

    id = Column(Integer, primary_key=True, index=True)
    optimized_route_id = Column(Integer, ForeignKey("optimized_routes.id"), nullable=False)
    
    stop_number = Column(Integer, nullable=False) # Sequence order
    waypoint_type = Column(String, nullable=False) # pickup, disposal_site, depot
    
    reference_id = Column(Integer, nullable=True) # ID of the Pickup or DisposalSite
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    is_completed = Column(Boolean, default=False)
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)

    optimized_route = relationship("OptimizedRoute", back_populates="waypoints")

    __table_args__ = (
        Index("ix_waypoint_route_order", "optimized_route_id", "stop_number"),
    )

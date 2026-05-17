from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Float, Numeric, Date, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
import enum
import datetime

class EventType(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PICKUP_CREATED = "PICKUP_CREATED"
    PICKUP_STARTED = "PICKUP_STARTED"
    PICKUP_COMPLETED = "PICKUP_COMPLETED"
    PICKUP_CANCELLED = "PICKUP_CANCELLED"
    WASTE_WEIGHED = "WASTE_WEIGHED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    SUB_UPGRADED = "SUB_UPGRADED"
    SUB_CANCELLED = "SUB_CANCELLED"
    FLEET_HEARTBEAT = "FLEET_HEARTBEAT"
    VEHICLE_MAINTENANCE = "VEHICLE_MAINTENANCE"
    SECURITY_ALERT = "SECURITY_ALERT"
    ESG_GOAL_REACHED = "ESG_GOAL_REACHED"

class AnalyticsEvent(Base, TimestampMixin):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    event_type = Column(Enum(EventType), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True) # e.g. "PICKUP", "INVOICE"
    entity_id = Column(String(100), nullable=True)
    
    event_metadata = Column(JSON, nullable=True)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")

    __table_args__ = (
        Index("ix_analytics_events_org_created", "organization_id", "created_at"),
        Index("ix_analytics_events_type_created", "event_type", "created_at"),
    )


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    total_pickups = Column(Integer, default=0)
    completed_pickups = Column(Integer, default=0)
    pending_pickups = Column(Integer, default=0)
    cancelled_pickups = Column(Integer, default=0)
    
    total_waste_kg = Column(Float, default=0.0)
    total_co2_saved_kg = Column(Float, default=0.0)
    
    active_drivers = Column(Integer, default=0)
    total_revenue = Column(Numeric(12, 2), default=0.00)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_daily_metrics_org_date", "organization_id", "date"),
    )


class PickupMetric(Base):
    __tablename__ = "pickup_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    waste_type = Column(String(50), nullable=False)
    total_weight = Column(Float, default=0.0)
    pickup_count = Column(Integer, default=0)

class DriverMetric(Base):
    __tablename__ = "driver_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    completed_pickups = Column(Integer, default=0)
    total_weight_handled = Column(Float, default=0.0)
    avg_rating = Column(Float, default=0.0)

class RevenueMetric(Base):
    __tablename__ = "revenue_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    successful_payments = Column(Integer, default=0)
    failed_payments = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0.00)
    refund_amount = Column(Numeric(12, 2), default=0.00)

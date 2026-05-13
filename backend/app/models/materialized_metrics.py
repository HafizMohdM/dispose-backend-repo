from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Numeric, Date, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
import datetime

class HourlyMetric(Base):
    __tablename__ = "hourly_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True) # Start of the hour
    
    total_pickups = Column(Integer, default=0)
    completed_pickups = Column(Integer, default=0)
    revenue = Column(Numeric(12, 2), default=0.00)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_hourly_metrics_org_ts", "organization_id", "timestamp"),
    )

class WeeklyMetric(Base):
    __tablename__ = "weekly_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    week_number = Column(Integer, nullable=False)
    
    total_pickups = Column(Integer, default=0)
    completed_pickups = Column(Integer, default=0)
    revenue = Column(Numeric(12, 2), default=0.00)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_weekly_metrics_org_year_week", "organization_id", "year", "week_number"),
    )

class MonthlyMetric(Base):
    __tablename__ = "monthly_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    total_pickups = Column(Integer, default=0)
    completed_pickups = Column(Integer, default=0)
    revenue = Column(Numeric(12, 2), default=0.00)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_monthly_metrics_org_year_month", "organization_id", "year", "month"),
    )

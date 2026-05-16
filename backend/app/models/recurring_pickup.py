from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.base import Base, TimestampMixin

class RecurringFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

class RecurringPickup(Base, TimestampMixin):
    __tablename__ = "recurring_pickups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    waste_type = Column(String, nullable=False)
    waste_weight = Column(Float, nullable=False)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    frequency = Column(SQLAlchemyEnum(RecurringFrequency, name="recurringfrequency"), nullable=False)
    next_run_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)

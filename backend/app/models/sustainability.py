from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
import datetime

class SustainabilityMetric(Base, TimestampMixin):
    """
    Tracks ESG (Environmental, Social, and Governance) data at the organization level.
    """
    __tablename__ = "sustainability_metrics"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    co2_saved_kg = Column(Float, default=0.0)
    waste_diverted_kg = Column(Float, default=0.0) # Waste sent to recycling/compost instead of landfill
    water_saved_liters = Column(Float, default=0.0)
    energy_saved_kwh = Column(Float, default=0.0)
    
    # Material breakdown for the day
    plastic_kg = Column(Float, default=0.0)
    paper_kg = Column(Float, default=0.0)
    metal_kg = Column(Float, default=0.0)
    organic_kg = Column(Float, default=0.0)
    other_kg = Column(Float, default=0.0)

    # Relationships
    organization = relationship("Organization")

    __table_args__ = (
        Index("ix_sust_metrics_org_date", "organization_id", "date"),
    )

class ESGGoal(Base, TimestampMixin):
    """
    Allows organizations to set and track environmental targets.
    """
    __tablename__ = "esg_goals"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    title = Column(String(100), nullable=False)
    goal_type = Column(String(50), nullable=False) # e.g. "CO2_REDUCTION", "RECYCLING_RATE"
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    unit = Column(String(20), nullable=False) # kg, liters, %, etc.
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="active") # active, achieved, failed

    organization = relationship("Organization")

import enum
from sqlalchemy import Enum, Boolean

class MetricType(str, enum.Enum):
    CO2_SAVED = "CO2_SAVED"
    WASTE_DIVERTED = "WASTE_DIVERTED"
    CLEAN_ENERGY = "CLEAN_ENERGY"
    ACTIVE_VEHICLES = "ACTIVE_VEHICLES"

class EcoGoal(Base):
    __tablename__ = "eco_goals"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    
    metric_type = Column(
        Enum(MetricType, native_enum=False, length=50),
        nullable=False
    )
    
    is_completed = Column(Boolean, default=False, nullable=False)
    deadline = Column(DateTime, nullable=True)

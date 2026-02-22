import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class WasteType(str, enum.Enum):
    GENERAL = "GENERAL"
    RECYCLABLE = "RECYCLABLE"
    HAZARDOUS = "HAZARDOUS"
    ORGANIC = "ORGANIC"
    ELECTRONIC = "ELECTRONIC"

class PickupStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Pickup(Base, TimestampMixin):
    __tablename__ = "pickups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    
    waste_type = Column(Enum(WasteType), nullable=False)
    waste_weight = Column(Float, nullable=False)
    
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    status = Column(Enum(PickupStatus), default=PickupStatus.PENDING, nullable=False, index=True)
    
    scheduled_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", backref="pickups")
    subscription = relationship("Subscription", backref="pickups")
    assignments = relationship("PickupAssignment", back_populates="pickup", cascade="all, delete-orphan")
    media = relationship("PickupMedia", back_populates="pickup", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("waste_weight >= 0", name="check_waste_weight_non_negative"),
    )

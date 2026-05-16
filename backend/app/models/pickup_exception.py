import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class ExceptionType(str, enum.Enum):
    GATE_LOCKED = "GATE_LOCKED"
    CUSTOMER_NOT_PRESENT = "CUSTOMER_NOT_PRESENT"
    HAZARDOUS_MATERIAL = "HAZARDOUS_MATERIAL"
    VOLUME_EXCEEDED = "VOLUME_EXCEEDED"
    ACCESS_DENIED = "ACCESS_DENIED"
    VEHICLE_ISSUE = "VEHICLE_ISSUE"
    OTHER = "OTHER"

class PickupException(Base, TimestampMixin):
    __tablename__ = "pickup_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickups.id", ondelete="CASCADE"), nullable=False, index=True)
    
    exception_type = Column(Enum(ExceptionType), nullable=False)
    notes = Column(Text, nullable=True)
    
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    pickup = relationship("Pickup", back_populates="exceptions")
    reported_by = relationship("User", foreign_keys=[reported_by_id], backref="reported_exceptions")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    __table_args__ = (
        Index("ix_pickup_exceptions_pickup_id", "pickup_id"),
        Index("ix_pickup_exceptions_type", "exception_type"),
        Index("ix_pickup_exceptions_resolved", "resolved"),
    )
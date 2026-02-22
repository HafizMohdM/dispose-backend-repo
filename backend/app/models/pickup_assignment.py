import enum
from sqlalchemy import Column, Integer, ForeignKey, Enum, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
from datetime import datetime

class AssignmentStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class PickupAssignment(Base, TimestampMixin):
    __tablename__ = "pickup_assignments"

    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickups.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(Enum(AssignmentStatus), default=AssignmentStatus.ASSIGNED, nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    pickup = relationship("Pickup", back_populates="assignments")
    driver = relationship("User", foreign_keys=[driver_id])
    
    __table_args__ = (
        UniqueConstraint("pickup_id", "status", name="uq_active_assignment_per_pickup"),
    )

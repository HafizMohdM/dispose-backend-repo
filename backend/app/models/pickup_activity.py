import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class ActivityType(str, enum.Enum):
    CREATED = "CREATED"
    STATUS_UPDATED = "STATUS_UPDATED"
    ASSIGNED = "ASSIGNED"
    UNASSIGNED = "UNASSIGNED"
    RESCHEDULED = "RESCHEDULED"
    EXCEPTION_REPORTED = "EXCEPTION_REPORTED"
    EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"
    MANUAL_NOTE = "MANUAL_NOTE"

class PickupActivity(Base, TimestampMixin):
    __tablename__ = "pickup_activities"

    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True) # Who did it
    
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(String(500), nullable=False) # Human readable (e.g., "Status changed from PENDING to ASSIGNED")
    notes = Column(Text, nullable=True) # For manual user notes
    
    # Stores dynamic data like old_status, new_status, old_date, new_date
    metadata_payload = Column(JSONB, nullable=True) 

    # Relationships
    pickup = relationship("Pickup", back_populates="activities")
    user = relationship("User") # Assuming you have a basic User model

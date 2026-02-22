import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime

class MediaType(str, enum.Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"

class PickupMedia(Base):
    __tablename__ = "pickup_media"

    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickups.id", ondelete="CASCADE"), nullable=False, index=True)
    
    media_url = Column(String(1000), nullable=False)
    media_type = Column(Enum(MediaType), nullable=False)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    pickup = relationship("Pickup", back_populates="media")

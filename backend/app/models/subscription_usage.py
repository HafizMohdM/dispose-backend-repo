from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class SubscriptionUsage(Base):
    __tablename__ = "subscription_usage"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), unique=True, nullable=False)
    
    pickups_used = Column(Integer, default=0, nullable=False)
    waste_weight_used = Column(Float, default=0.0, nullable=False)
    drivers_used = Column(Integer, default=0, nullable=False)
    
    last_reset_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    subscription = relationship("Subscription", back_populates="usage")

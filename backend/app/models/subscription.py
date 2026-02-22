from sqlalchemy import Column, Integer, Boolean, ForeignKey, Enum, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
import enum

class SubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    auto_renew = Column(Boolean, default=True, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    upgraded_from_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    # Relationships
    plan = relationship("SubscriptionPlan")
    organization = relationship("Organization")
    usage = relationship("SubscriptionUsage", back_populates="subscription", uselist=False)

    __table_args__ = (
        Index('ix_subscriptions_org_status', 'organization_id', 'status'),
        # Note: partial unique index for ACTIVE subscriptions would be ideal, but Alembic handling varies.
        # UniqueConstraint is added to schema, but logic will also enforce unique ACTIVE per organization.
    )

from sqlalchemy import Column, Integer, String, Text, Enum, Numeric, Boolean, Float, CheckConstraint, Index
from app.models.base import Base, TimestampMixin
import enum

class CategoryType(str, enum.Enum):
    APARTMENT = "APARTMENT"
    HOUSEHOLD = "HOUSEHOLD"
    INDIVIDUAL = "INDIVIDUAL"
    COMMERCIAL = "COMMERCIAL"
    OTHERS = "OTHERS"

class PricingModel(str, enum.Enum):
    FIXED = "FIXED"
    PER_UNIT = "PER_UNIT"
    PER_MEMBER = "PER_MEMBER"
    CUSTOM = "CUSTOM"

class BillingCycle(str, enum.Enum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class SubscriptionPlan(Base, TimestampMixin):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    category_type = Column(Enum(CategoryType), nullable=False, index=True)
    pricing_model = Column(Enum(PricingModel), nullable=False)
    
    price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(Enum(BillingCycle), nullable=False)
    
    max_units = Column(Integer, nullable=True)
    max_members = Column(Integer, nullable=True)
    pickup_limit = Column(Integer, nullable=False, default=0)
    waste_weight_limit = Column(Float, nullable=False, default=0.0)
    driver_limit = Column(Integer, nullable=False, default=0)
    
    is_visible = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_non_negative'),
        CheckConstraint('pickup_limit >= 0', name='check_pickup_limit_non_negative'),
    )

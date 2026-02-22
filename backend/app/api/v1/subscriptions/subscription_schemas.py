from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.subscription_plan import CategoryType, PricingModel, BillingCycle
from app.models.subscription import SubscriptionStatus

class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_type: CategoryType
    pricing_model: PricingModel
    price: Decimal
    billing_cycle: BillingCycle
    max_units: Optional[int] = None
    max_members: Optional[int] = None
    pickup_limit: int = 0
    waste_weight_limit: float = 0.0
    driver_limit: int = 0
    is_visible: bool = True
    is_active: bool = True

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_type: Optional[CategoryType] = None
    pricing_model: Optional[PricingModel] = None
    price: Optional[Decimal] = None
    billing_cycle: Optional[BillingCycle] = None
    max_units: Optional[int] = None
    max_members: Optional[int] = None
    pickup_limit: Optional[int] = None
    waste_weight_limit: Optional[float] = None
    driver_limit: Optional[int] = None
    is_visible: Optional[bool] = None
    is_active: Optional[bool] = None

class PlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category_type: CategoryType
    pricing_model: PricingModel
    price: Decimal
    billing_cycle: BillingCycle
    max_units: Optional[int] = None
    max_members: Optional[int] = None
    pickup_limit: int
    waste_weight_limit: float
    driver_limit: int
    is_visible: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SubscriptionResponse(BaseModel):
    id: int
    organization_id: int
    plan_id: int
    start_date: datetime
    end_date: datetime
    status: SubscriptionStatus
    auto_renew: bool
    cancelled_at: Optional[datetime] = None
    upgraded_from_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    plan: PlanResponse

    model_config = ConfigDict(from_attributes=True)

class SubscribeRequest(BaseModel):
    plan_id: int

class UpgradeRequest(BaseModel):
    new_plan_id: int

class UsageResponse(BaseModel):
    id: int
    subscription_id: int
    pickups_used: int
    waste_weight_used: float
    drivers_used: int
    last_reset_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

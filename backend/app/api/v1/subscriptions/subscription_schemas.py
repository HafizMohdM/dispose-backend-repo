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

class CheckoutRequest(BaseModel):
    target_plan_id: int

class CheckoutSessionData(BaseModel):
    order_id: Optional[str] = None
    key: Optional[str] = None
    amount: Optional[int] = None  # in paise
    currency: Optional[str] = None

class CheckoutResponse(BaseModel):
    payment_id: Optional[str] = None
    invoice_id: Optional[str] = None
    gateway: str
    amount: float  # in INR
    status: str    # "SUCCESS" or "INITIATED"
    message: Optional[str] = None
    session_data: Optional[CheckoutSessionData] = None

# Entitlements
class LimitsDict(BaseModel):
    pickup_limit: int
    waste_weight_limit: float
    driver_limit: int

class UsageDict(BaseModel):
    pickups_used: int
    waste_weight_used: float
    drivers_used: int

class RemainingDict(BaseModel):
    pickups: int
    waste_weight: float
    drivers: int

class EntitlementResponse(BaseModel):
    plan_name: str
    plan_category: str
    status: str
    grace_period_end: Optional[datetime] = None
    limits: LimitsDict
    usage: UsageDict
    remaining: RemainingDict

# Check Limits
class CheckLimitRequest(BaseModel):
    resource: str  # "pickups", "waste_weight", "drivers"
    quantity: float = 1.0

class CheckLimitResponse(BaseModel):
    allowed: bool
    current_usage: float
    limit: float
    remaining: float
    message: Optional[str] = None

# Time-series Usage History
class UsageHistoryPoint(BaseModel):
    date: str  # YYYY-MM-DD
    pickups_used: int
    waste_weight_used: float
    drivers_used: int

class UsageHistoryResponse(BaseModel):
    organization_id: int
    history: list[UsageHistoryPoint]

# Revenue Summary
class RevenueSummaryResponse(BaseModel):
    mrr: float
    arr: float
    total_cash_collected: float
    active_subscriptions_count: int
    churn_rate: float

# Payments History
class PaymentHistoryPoint(BaseModel):
    payment_id: str
    invoice_id: str
    amount: float
    status: str
    gateway: str
    gateway_payment_id: Optional[str] = None
    invoice_status: str
    organization_name: str
    created_at: datetime

class PaymentHistoryResponse(BaseModel):
    payments: list[PaymentHistoryPoint]

# Coupons
class ApplyCouponRequest(BaseModel):
    coupon_code: str

# Trials
class StartTrialRequest(BaseModel):
    plan_id: int

# Enterprise Contracts
class ContractResponse(BaseModel):
    id: int
    organization_id: int
    plan_name: str
    status: str
    sla_covenants: list[str]
    terms_pdf_url: Optional[str] = None
    created_at: datetime

# Refunds
class RefundRequest(BaseModel):
    payment_id: str
    reason: Optional[str] = None



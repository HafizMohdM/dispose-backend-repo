from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.dependencies import get_current_user, get_user_org
from app.models.user import User
from app.models.role_mapping import UserRole
from app.models.organization import Organization

from app.api.v1.subscriptions.subscription_schemas import (
    PlanCreate,
    PlanUpdate,
    PlanResponse,
    SubscriptionResponse,
    SubscribeRequest,
    UpgradeRequest,
    UsageResponse,
    CheckoutRequest,
    CheckoutResponse,
    EntitlementResponse,
    CheckLimitRequest,
    CheckLimitResponse,
    UsageHistoryResponse,
    RevenueSummaryResponse,
    ApplyCouponRequest,
    StartTrialRequest,
    ContractResponse
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()

@router.get("/plans", response_model=list[PlanResponse])
def get_plans(
    db: Session = Depends(get_db)
):
    return SubscriptionService.list_plans(db)

@router.post("/plans", response_model=PlanResponse, dependencies=[Depends(require_permission("subscription.manage"))])
def create_plan(
    request: PlanCreate,
    db: Session = Depends(get_db)
):
    return SubscriptionService.create_plan(db, request)

@router.patch("/plans/{plan_id}", response_model=PlanResponse, dependencies=[Depends(require_permission("subscription.manage"))])
def update_plan(
    plan_id: int,
    request: PlanUpdate,
    db: Session = Depends(get_db)
):
    return SubscriptionService.update_plan(db, plan_id, request)

@router.delete("/plans/{plan_id}", dependencies=[Depends(require_permission("subscription.manage"))])
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    return SubscriptionService.delete_plan(db, plan_id)

@router.post("/subscribe", response_model=SubscriptionResponse)
def subscribe(
    request: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.subscribe(db, org, request.plan_id)

@router.get("/my", response_model=SubscriptionResponse)
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.get_my_subscription(db, org.id)

@router.post("/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.cancel_subscription(db, org.id)

@router.post("/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    request: UpgradeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.upgrade_subscription(db, org.id, request.new_plan_id)

@router.get("/usage", response_model=UsageResponse)
def get_usage(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    sub = SubscriptionService.get_my_subscription(db, org.id)
    return SubscriptionService.get_usage(db, sub.id)


@router.post("/trigger-dunning", dependencies=[Depends(require_permission("subscription.manage"))])
def trigger_dunning(
    db: Session = Depends(get_db)
):
    from app.tasks.subscription_tasks import process_dunning_and_suspensions
    res = process_dunning_and_suspensions()
    return {"status": "success", "result": res}


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_order(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.create_checkout_order(db, org.id, request.target_plan_id)


@router.get("/entitlements", response_model=EntitlementResponse)
def get_entitlements(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.get_entitlements(db, org.id)


@router.post("/check-limit", response_model=CheckLimitResponse)
def check_limit(
    request: CheckLimitRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.check_limit(db, org.id, request.resource, request.quantity)


@router.get("/usage-history", response_model=UsageHistoryResponse)
def get_usage_history(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.get_usage_history(db, org.id)


@router.get("/revenue-summary", response_model=RevenueSummaryResponse)
def get_revenue_summary(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.manage"))
):
    return SubscriptionService.get_revenue_summary(db)


@router.post("/start-trial", response_model=SubscriptionResponse)
def start_trial(
    request: StartTrialRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.start_trial(db, org, request.plan_id)


@router.post("/apply-coupon")
def apply_coupon(
    request: ApplyCouponRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.apply_coupon(db, org.id, request.coupon_code)


@router.get("/contracts", response_model=list[ContractResponse])
def get_contracts(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    org = get_user_org(db, current_user)
    return SubscriptionService.get_contracts(db, org.id)



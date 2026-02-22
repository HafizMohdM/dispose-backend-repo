from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.dependencies import get_current_user
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
    UsageResponse
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscription", tags=["Subscriptions"])

def get_user_org(db: Session, user: User) -> Organization:
    user_role = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if not user_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    org = db.query(Organization).filter(Organization.id == user_role.org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org

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

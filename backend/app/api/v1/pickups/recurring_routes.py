from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.dependencies import get_user_org, UsageEnforcer
from app.models.user import User

from app.api.v1.pickups.recurring_schemas import RecurringPickupCreateRequest, RecurringPickupResponse
from app.repositories.recurring_pickup_repo import RecurringPickupRepository
from app.api.v1.pickups.recurring_service import RecurringPickupService

router = APIRouter()

@router.post("/", response_model=RecurringPickupResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring_pickup(
    request: RecurringPickupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage")),
    _quota = Depends(UsageEnforcer("pickups"))
):
    """Create a new recurring pickup rule"""
    org = get_user_org(db, current_user)
    if not org:
        raise HTTPException(status_code=400, detail="Organization context required")
    return RecurringPickupService.create_recurring_pickup(db, org.id, request)

@router.get("/", response_model=List[RecurringPickupResponse])
async def list_recurring_pickups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """List all recurring pickup rules for the organization"""
    org = get_user_org(db, current_user)
    if not org:
        raise HTTPException(status_code=400, detail="Organization context required")
    return RecurringPickupRepository.get_by_org(db, org.id)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.dependencies import get_db, get_user_org
from app.models.user import User
from app.models.pickup_exception import ExceptionType
from app.repositories.pickup_exception_repo import PickupExceptionRepository
from app.api.v1.pickups.pickup_exception_schemas import (
    PickupExceptionResponse,
    PickupExceptionListResponse,
    PickupExceptionStatsResponse
)

router = APIRouter()

@router.get("/", response_model=PickupExceptionListResponse)
def list_exceptions(
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    exception_type: Optional[ExceptionType] = Query(None, description="Filter by exception type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start reported date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end reported date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """
    Get a filtered list of exceptions reported for pickups.
    - Admins see all exceptions.
    - Organization members see exceptions for their organization only.
    """
    is_admin = any(rm.role.name == "ADMIN" for rm in current_user.roles)
    org_id = None
    if not is_admin:
        org = get_user_org(db, current_user)
        org_id = org.id
        
    exceptions = PickupExceptionRepository.get_filtered_exceptions(
        db=db,
        organization_id=org_id,
        resolved=resolved,
        exception_type=exception_type,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    
    total = PickupExceptionRepository.count_filtered_exceptions(
        db=db,
        organization_id=org_id,
        resolved=resolved,
        exception_type=exception_type,
        start_date=start_date,
        end_date=end_date
    )
    
    return {"exceptions": exceptions, "total": total}


@router.get("/stats", response_model=PickupExceptionStatsResponse)
def get_exceptions_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """
    Get exception analytics and categorical breakdowns.
    - Admins see global metrics.
    - Organization members see their organization's metrics only.
    """
    is_admin = any(rm.role.name == "ADMIN" for rm in current_user.roles)
    org_id = None
    if not is_admin:
        org = get_user_org(db, current_user)
        org_id = org.id
        
    stats = PickupExceptionRepository.get_exceptions_stats(db, org_id)
    return stats


@router.get("/{exception_id}", response_model=PickupExceptionResponse)
def get_exception_detail(
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """
    Retrieve single exception details. Enforces organization ownership.
    """
    exception = PickupExceptionRepository.get_exception_by_id(db, exception_id)
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    # Ownership verification
    is_admin = any(rm.role.name == "ADMIN" for rm in current_user.roles)
    if not is_admin:
        org = get_user_org(db, current_user)
        if exception.pickup.organization_id != org.id:
            raise HTTPException(status_code=403, detail="Exception does not belong to your organization")
            
    return exception


@router.post("/{exception_id}/resolve", response_model=PickupExceptionResponse)
def resolve_exception_route(
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """
    Resolve an exception reported for a pickup.
    - Admins can resolve any exception.
    - Organization dispatchers/managers can resolve exceptions belonging to their organization.
    """
    exception = PickupExceptionRepository.get_exception_by_id(db, exception_id)
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    is_admin = any(rm.role.name == "ADMIN" for rm in current_user.roles)
    if not is_admin:
        org = get_user_org(db, current_user)
        if exception.pickup.organization_id != org.id:
            raise HTTPException(status_code=403, detail="Exception does not belong to your organization")
            
    resolved = PickupExceptionRepository.resolve_exception(
        db=db,
        exception_id=exception_id,
        resolved_by_id=current_user.id
    )
    db.commit()
    db.refresh(resolved)
    return resolved

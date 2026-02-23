from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.permissions import require_permission
from app.api.v1.pickups.pickup_schemas import (
    PickupCreateRequest, 
    PickupResponse, 
    PickupUpdateStatusRequest, 
    PickupAssignmentResponse,
    PickupListResponse
)
from app.api.v1.pickups.pickup_service import PickupService
from app.models.pickup import PickupStatus
from app.models.pickup_assignment import AssignmentStatus
from app.models.user import User

from app.core.dependencies import get_db, get_user_org
from app.core.permissions import require_permission

router = APIRouter(prefix="/pickups", tags=["Pickups"])

@router.post("/", response_model=PickupResponse, status_code=status.HTTP_201_CREATED)
def create_pickup(
    request: PickupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.create"))
):
    """
    Creates a new pickup for the user's organization.
    Validates subscription, limits, and inherently increments usage safely.
    """
    org = get_user_org(db, current_user)
    return PickupService.create_pickup(db, org, request)


@router.get("/", response_model=PickupListResponse)
def list_pickups(
    p_status: PickupStatus = None,
    a_status: AssignmentStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """
    Lists pickups based on the user's role.
    - DRIVER: sees assigned pickups
    - ADMIN: sees all
    - ORG/DEFAULT: sees organization's pickups
    """
    # Simple role check (assuming roles are properly mapped and populated, using admin check for now)
    # A complete solution would check the permissions table.
    is_admin = False
    is_driver = False
    
    # Check if admin
    for role_mapping in current_user.roles:
        if role_mapping.role.name == "ADMIN":
            is_admin = True
        if role_mapping.role.name == "DRIVER":
            is_driver = True

    if is_admin:
        pickups = PickupService.list_all_pickups(db, p_status)
    elif is_driver:
        pickups = PickupService.list_pickups_for_driver(db, current_user.id, a_status)
    else:
        org = get_user_org(db, current_user)
        pickups = PickupService.list_pickups_for_org(db, org.id, p_status)
        
    return {"pickups": pickups, "total": len(pickups)}


@router.get("/{pickup_id}", response_model=PickupResponse)
def get_pickup(
    pickup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """
    Get a specific pickup by ID. Ensures the user is authorized to see it.
    """
    pickup = PickupService.get_pickup_by_id(db, pickup_id)
    
    # Authorization checks
    is_admin = any(rm.role.name == "ADMIN" for rm in current_user.roles)
    is_driver = any(rm.role.name == "DRIVER" for rm in current_user.roles)
    
    if not is_admin:
        if is_driver:
            # Check if assigned
            if not any(assignment.driver_id == current_user.id for assignment in pickup.assignments):
                raise HTTPException(status_code=403, detail="Not assigned to this pickup")
        else:
            # Check if org owns it
            org = get_user_org(db, current_user)
            if pickup.organization_id != org.id:
                raise HTTPException(status_code=403, detail="Pickup does not belong to your organization")
                
    return pickup


@router.patch("/{pickup_id}/status", response_model=PickupResponse)
def update_pickup_status(
    pickup_id: int,
    request: PickupUpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """
    Updates the status of a pickup following rigid state transitions.
    Drivers can complete pickups; Admins/Orgs can cancel them.
    """
    is_admin = any(rm.role.name == "ADMIN" for rm in current_user.roles)
    return PickupService.update_pickup_status(db, pickup_id, request, current_user, is_admin)


@router.post("/{pickup_id}/assign", response_model=PickupAssignmentResponse)
def assign_driver(
    pickup_id: int,
    driver_id: int,
    db: Session = Depends(get_db),
    # Only admins or dispatchers can assign
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """
    Assigns a driver to a pending pickup.
    Transitions pickup to ASSIGNED.
    """
    # Assuming assigning requires an explicitly elevated role check beyond just pickup.manage if needed
    return PickupService.assign_driver(db, pickup_id, driver_id)

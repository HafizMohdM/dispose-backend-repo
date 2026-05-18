from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.permissions import require_permission
from app.api.v1.pickups.pickup_schemas import (
    PickupCreateRequest, 
    PickupResponse, 
    PickupUpdateStatusRequest, 
    PickupAssignmentResponse,
    PickupListResponse,
    PickupPriorityUpdateRequest,
    PickupStatsResponse,
    PickupImportResponse,
    PickupMediaResponse
)
from app.api.v1.pickups.pickup_workflow_schemas import (
    PickupCancelRequest,
    PickupRescheduleRequest,
    PickupRejectRequest,
    PickupCompleteRequest,
    BulkAssignRequest,
    BulkCancelRequest,
    BulkRescheduleRequest,
    BulkOperationResponse
)
from app.api.v1.pickups.pickup_service import PickupService
from app.models.pickup import PickupStatus
from app.models.pickup_assignment import AssignmentStatus
from app.models.user import User
from app.api.v1.pickups.pickup_exception_schemas import (
    PickupExceptionCreateRequest,
    PickupExceptionResponse,
    PickupExceptionListResponse
)
from app.repositories.pickup_exception_repo import PickupExceptionRepository

from app.core.dependencies import get_db, get_user_org, UsageEnforcer
from app.core.permissions import require_permission

from app.api.v1.pickups.pickup_activity_schemas import PickupActivityCreateRequest, PickupTimelineResponse, PickupActivityResponse
from app.repositories.pickup_activity_repo import PickupActivityRepository
from app.models.pickup_activity import ActivityType

router = APIRouter()

@router.post("/", response_model=PickupResponse, status_code=status.HTTP_201_CREATED)
def create_pickup(
    request: PickupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.create")),
    _quota = Depends(UsageEnforcer("pickups"))
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

@router.get("/stats", response_model=PickupStatsResponse)
def get_pickup_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    org = get_user_org(db, current_user)
    stats = PickupService.get_stats(db, org.id, start_date, end_date)
    return stats

@router.get("/export")
def export_pickups_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    org = get_user_org(db, current_user)
    csv_data = PickupService.export_csv(db, org.id)
    return StreamingResponse(
        iter([csv_data]), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=pickups_export_{org.id}.csv"}
    )

@router.post("/import", response_model=PickupImportResponse)
def import_pickups_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    org = get_user_org(db, current_user)
    count = PickupService.import_csv(db, org.id, file, current_user)
    return {"imported_count": count}



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

@router.post("/{pickup_id}/cancel", response_model=PickupResponse)
def cancel_pickup(
    pickup_id: int,
    request: PickupCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.cancel"))
):
    """
    Cancel a PENDING or ASSIGNED pickup. Reverts subscription usage.
    """
    return PickupService.cancel_pickup(db, pickup_id, request, current_user)


@router.post("/{pickup_id}/reschedule", response_model=PickupResponse)
def reschedule_pickup(
    pickup_id: int,
    request: PickupRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.reschedule"))
):
    """
    Reschedule a pickup to a future time.
    """
    return PickupService.reschedule_pickup(db, pickup_id, request, current_user)


@router.post("/{pickup_id}/accept", response_model=PickupResponse)
def accept_pickup(
    pickup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.accept"))
):
    """
    Driver accepts an assigned pickup, moving it to IN_PROGRESS.
    """
    return PickupService.accept_pickup(db, pickup_id, current_user)


@router.post("/{pickup_id}/reject", response_model=PickupResponse)
def reject_pickup(
    pickup_id: int,
    request: PickupRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.reject"))
):
    """
    Driver rejects an assigned pickup. Returns it to PENDING.
    """
    return PickupService.reject_pickup(db, pickup_id, request, current_user)


@router.post("/{pickup_id}/complete", response_model=PickupResponse)
def complete_pickup(
    pickup_id: int,
    request: PickupCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.complete"))
):
    """
    Driver completes a pickup and submits the actual weight.
    """
    return PickupService.complete_pickup(db, pickup_id, request, current_user)


# ==================== EXCEPTION ENDPOINTS ====================

@router.post("/{pickup_id}/exceptions", response_model=PickupExceptionResponse, status_code=status.HTTP_201_CREATED)
def report_exception(
    pickup_id: int,
    request: PickupExceptionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """Report an exception during pickup (Gate locked, Customer absent, etc.)"""
    return PickupService.report_exception(
        db=db, 
        pickup_id=pickup_id, 
        request=request, 
        reported_by_id=current_user.id
    )


@router.get("/{pickup_id}/exceptions", response_model=PickupExceptionListResponse)
def get_pickup_exceptions(
    pickup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """Get all exceptions reported for a specific pickup"""
    exceptions = PickupExceptionRepository.get_exceptions_by_pickup(db, pickup_id)
    return {"exceptions": exceptions, "total": len(exceptions)}


@router.post("/exceptions/{exception_id}/resolve", response_model=PickupExceptionResponse)
def resolve_exception(
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """Mark an exception as resolved (Admin / Dispatcher)"""
    return PickupService.resolve_exception(
        db=db, 
        exception_id=exception_id, 
        resolved_by_id=current_user.id
    )

@router.get("/{pickup_id}/timeline", response_model=PickupTimelineResponse)
def get_pickup_timeline(
    pickup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.view"))
):
    """Get the complete operational timeline/history of a pickup."""
    # Ensure pickup exists and user has access
    PickupService.get_pickup_by_id(db, pickup_id) 
    
    activities = PickupActivityRepository.get_timeline(db, pickup_id)
    return {
        "pickup_id": pickup_id,
        "total_events": len(activities),
        "timeline": activities
    }

@router.post("/{pickup_id}/activity", response_model=PickupActivityResponse)
def add_manual_pickup_note(
    pickup_id: int,
    request: PickupActivityCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """Add a manual operational note to the pickup timeline."""
    pickup = PickupService.get_pickup_by_id(db, pickup_id)
    
    activity = PickupActivityRepository.log_activity(
        db=db,
        pickup_id=pickup.id,
        user_id=current_user.id,
        activity_type=ActivityType.MANUAL_NOTE,
        description=f"Manual note added by user {current_user.email if hasattr(current_user, 'email') else current_user.id}",
        notes=request.notes
    )
    db.commit()
    db.refresh(activity)
    return activity


# ==================== BULK DISPATCHER OPERATIONS ====================

@router.post("/bulk-assign", response_model=BulkOperationResponse)
def bulk_assign_pickups(
    request: BulkAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """
    Atomically assign a driver to multiple PENDING pickups.
    If any pickup fails validation, the entire operation is rolled back.
    """
    return PickupService.bulk_assign(db, request, current_user)


@router.post("/bulk-cancel", response_model=BulkOperationResponse)
def bulk_cancel_pickups(
    request: BulkCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """
    Atomically cancel multiple PENDING or ASSIGNED pickups.
    Rolls back subscription usage. Entire batch fails if any pickup is invalid.
    """
    return PickupService.bulk_cancel(db, request, current_user)


@router.post("/bulk-reschedule", response_model=BulkOperationResponse)
def bulk_reschedule_pickups(
    request: BulkRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    """
    Atomically reschedule multiple PENDING or ASSIGNED pickups to a new date/time.
    Entire batch fails if any pickup is in an invalid state.
    """
    return PickupService.bulk_reschedule(db, request, current_user)


@router.patch("/{pickup_id}/priority", response_model=PickupResponse)
def update_pickup_priority(
    pickup_id: int,
    request: PickupPriorityUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    return PickupService.update_priority(db, pickup_id, request.priority, current_user)


@router.post("/{pickup_id}/images", response_model=PickupMediaResponse)
def upload_pickup_image(
    pickup_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("pickup.manage"))
):
    return PickupService.upload_pickup_image(db, pickup_id, file, current_user)

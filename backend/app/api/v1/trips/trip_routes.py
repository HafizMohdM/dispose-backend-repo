from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission

from app.services.trip_service import TripService
from app.api.v1.trips.trip_schemas import (
    TripCreate,
    TripResponse,
    TripStatusUpdateRequest
)

router = APIRouter()

def get_org_id(current_user, request_org_id: Optional[int] = None) -> int:
    org_id = request_org_id or getattr(current_user, "current_org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required."
        )
    return org_id

@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trip(
    request: TripCreate,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = TripService(db)
    return service.create_trip(org_id, request)

@router.get(
    "",
    response_model=List[TripResponse],
)
def list_trips(
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = TripService(db)
    return service.list_trips(org_id, skip, limit)

@router.get(
    "/{trip_id}",
    response_model=TripResponse,
)
def get_trip(
    trip_id: UUID,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = TripService(db)
    return service.get_trip(trip_id, org_id)

@router.patch(
    "/{trip_id}/status",
    response_model=TripResponse,
)
def update_trip_status(
    trip_id: UUID,
    request: TripStatusUpdateRequest,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = TripService(db)
    return service.update_trip_status(trip_id, org_id, request.status)

@router.post(
    "/{trip_id}/pause",
    response_model=TripResponse,
)
def pause_trip(
    trip_id: UUID,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = TripService(db)
    from app.models.trip import TripStatus
    return service.update_trip_status(trip_id, org_id, TripStatus.PAUSED)

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission

from app.services.incident_service import IncidentService
from app.api.v1.incidents.incident_schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentResolveRequest
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
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_incident(
    request: IncidentCreate,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("incident.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = IncidentService(db)
    return service.report_incident(
        organization_id=org_id,
        incident_type=request.incident_type,
        description=request.description,
        severity=request.severity,
        reported_by=current_user.id,
        vehicle_id=request.vehicle_id,
        driver_id=request.driver_id,
        trip_id=request.trip_id,
        latitude=request.latitude,
        longitude=request.longitude
    )

@router.get(
    "",
    response_model=List[IncidentResponse],
)
def list_incidents(
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("incident.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = IncidentService(db)
    return service.list_incidents(org_id, skip, limit)

@router.patch(
    "/{incident_id}/resolve",
    response_model=IncidentResponse,
)
def resolve_incident(
    incident_id: UUID,
    request: IncidentResolveRequest,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("incident.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = IncidentService(db)
    return service.resolve_incident(
        incident_id=incident_id,
        organization_id=org_id,
        resolved_by=current_user.id,
        resolution_notes=request.resolution_notes
    )

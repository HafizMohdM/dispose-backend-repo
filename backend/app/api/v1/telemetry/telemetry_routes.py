from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission

from app.services.telemetry_service import TelemetryService
from app.api.v1.telemetry.telemetry_schemas import (
    TelemetryIngestRequest,
    TelemetryResponse
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
    "/{vehicle_id}",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_telemetry(
    vehicle_id: UUID,
    request: TelemetryIngestRequest,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    """
    Ingest telemetry data for a vehicle. Requires vehicle.manage or valid device token.
    (Device token validation is delegated to a separate dependency or middleware if applicable)
    """
    org_id = get_org_id(current_user, organization_id)
    service = TelemetryService(db)
    
    return await service.ingest_telemetry(
        vehicle_id=vehicle_id,
        organization_id=org_id,
        payload=request
    )

@router.get(
    "/{vehicle_id}/latest",
    response_model=TelemetryResponse,
)
def get_latest_telemetry(
    vehicle_id: UUID,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.view")),
):
    """
    Retrieve the latest telemetry for a given vehicle.
    """
    org_id = get_org_id(current_user, organization_id)
    service = TelemetryService(db)
    
    return service.get_latest_telemetry(
        vehicle_id=vehicle_id,
        organization_id=org_id
    )

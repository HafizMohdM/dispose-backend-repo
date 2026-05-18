from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission

from app.services.vehicle_service import VehicleService
from app.api.v1.vehicles.vehicle_schemas import (
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
    AssignDriverRequest,
    VehicleAssignmentResponse,
    VehicleMaintenanceCreate,
    VehicleMaintenanceResponse,
    FleetHealthResponse
)

router = APIRouter()

def get_org_id(current_user, request_org_id: Optional[int] = None) -> int:
    org_id = request_org_id or getattr(current_user, "current_org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required. Admins must provide it in the request."
        )
    return org_id

@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    request: VehicleCreate,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.create_vehicle(org_id, request)

@router.get(
    "",
    response_model=List[VehicleResponse],
)
def list_vehicles(
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.list_vehicles(org_id, skip, limit)

@router.get(
    "/health",
    response_model=FleetHealthResponse,
)
def get_fleet_health(
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.get_fleet_health(org_id)

@router.get(
    "/maintenance",
    response_model=List[VehicleMaintenanceResponse],
)
def list_maintenances(
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.list_maintenances(org_id, skip, limit)

@router.post(
    "/{vehicle_id}/maintenance",
    response_model=VehicleMaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance(
    vehicle_id: int,
    request: VehicleMaintenanceCreate,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.create_maintenance(vehicle_id, org_id, request)

@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
)
def get_vehicle(
    vehicle_id: int,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.view")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.get_vehicle(vehicle_id, org_id)

@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
)
def update_vehicle(
    vehicle_id: int,
    request: VehicleUpdate,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    return service.update_vehicle(vehicle_id, org_id, request)

@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vehicle(
    vehicle_id: int,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    service = VehicleService(db)
    service.delete_vehicle(vehicle_id, org_id)
    return None

@router.post(
    "/{vehicle_id}/assign-driver",
    response_model=VehicleAssignmentResponse,
    status_code=status.HTTP_200_OK,
)
def assign_driver(
    vehicle_id: int,
    request_data: AssignDriverRequest,
    request: Request,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    ip_address = request.client.host if request.client else None
    service = VehicleService(db)
    return service.assign_driver(vehicle_id, request_data.driver_id, org_id, current_user.id, ip_address)

@router.post(
    "/{vehicle_id}/unassign-driver",
    status_code=status.HTTP_200_OK,
)
def unassign_driver(
    vehicle_id: int,
    request: Request,
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("vehicle.manage")),
):
    org_id = get_org_id(current_user, organization_id)
    ip_address = request.client.host if request.client else None
    service = VehicleService(db)
    service.unassign_driver(vehicle_id, org_id, current_user.id, ip_address)
    return {"status": "success", "message": "Driver unassigned successfully"}

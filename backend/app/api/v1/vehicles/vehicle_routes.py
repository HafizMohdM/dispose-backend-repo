from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.vehicles.vehicle_schemas import VehicleCreate, VehicleResponse, VehicleAssignmentRequest, MaintenanceLogCreate
from app.repositories.vehicle_repo import VehicleRepository
from app.models.vehicle import Vehicle, MaintenanceLog
from app.core.dependencies import get_user_org
from typing import List

router = APIRouter()

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def add_vehicle(
    request: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Onboards a new vehicle into the organization's fleet.
    """
    org = get_user_org(db, current_user)
    vehicle = Vehicle(
        organization_id=org.id,
        **request.dict()
    )
    new_vehicle = VehicleRepository.create_vehicle(db, vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle

@router.get("/", response_model=List[VehicleResponse])
def list_vehicles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns the complete list of vehicles for the organization.
    """
    org = get_user_org(db, current_user)
    return VehicleRepository.get_vehicles_by_org(db, org.id)

@router.get("/{id}", response_model=VehicleResponse)
def get_vehicle(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns details for a specific vehicle, including current health stats.
    """
    vehicle = VehicleRepository.get_vehicle_by_id(db, id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.post("/{id}/assign-driver")
def assign_driver(
    id: int,
    request: VehicleAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Assigns a driver to a vehicle. Automatically unassigns them from any other active vehicle.
    """
    VehicleRepository.assign_driver(db, id, request.driver_id)
    db.commit()
    return {"status": "assigned"}

@router.post("/{id}/maintenance")
def log_maintenance(
    id: int,
    request: MaintenanceLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Logs a maintenance event for a vehicle.
    """
    log = MaintenanceLog(
        vehicle_id=id,
        **request.dict()
    )
    VehicleRepository.create_maintenance_log(db, log)
    db.commit()
    return {"status": "log_created"}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.telemetry.telemetry_schemas import TelemetryIngestRequest, DiagnosticResponse
from app.services.telemetry_service import TelemetryService
from app.repositories.telemetry_repo import TelemetryRepository
from app.repositories.vehicle_repo import VehicleRepository
from app.core.dependencies import get_user_org

router = APIRouter()

@router.post("/ingest")
async def ingest_telemetry(
    request: TelemetryIngestRequest,
    db: Session = Depends(get_db)
):
    """
    High-throughput endpoint for IoT devices to stream sensor data.
    """
    # 1. Validate Device
    device = TelemetryRepository.get_device_by_identifier(db, request.device_identifier)
    if not device:
        raise HTTPException(status_code=404, detail="Device not recognized")
    
    if not device.vehicle_id:
        raise HTTPException(status_code=400, detail="Device not assigned to a vehicle")

    # 2. Get Vehicle & Org for scoped broadcasting
    vehicle = VehicleRepository.get_vehicle_by_id(db, device.vehicle_id)
    
    await TelemetryService.ingest_data(
        db=db,
        device_id=device.id,
        vehicle_id=vehicle.id,
        org_id=vehicle.organization_id,
        data=request.dict()
    )
    
    return {"status": "success"}

@router.get("/{vehicle_id}/live", response_model=DiagnosticResponse)
async def get_live_diagnostics(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns the most recent diagnostic snapshot for a vehicle.
    """
    org = get_user_org(db, current_user)
    vehicle = VehicleRepository.get_vehicle_by_id(db, vehicle_id)
    if not vehicle or vehicle.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this vehicle's telemetry")

    diag = TelemetryRepository.get_latest_diagnostics(db, vehicle_id)
    if not diag:
        raise HTTPException(status_code=404, detail="No telemetry data found for this vehicle")
    
    return diag

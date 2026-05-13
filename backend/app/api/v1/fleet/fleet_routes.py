from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.fleet.fleet_schemas import LocationStreamRequest, FleetLiveResponse
from app.services.fleet_service import FleetService
from app.repositories.fleet_repo import FleetRepository
from app.core.dependencies import get_user_org

router = APIRouter()

@router.post("/drivers/{id}/heartbeat")
async def driver_heartbeat(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.track"))
):
    """
    Updates driver online status and keeps tracking session active.
    """
    org = get_user_org(db, current_user)
    # Ensure current_user matches ID or is admin
    if current_user.id != id and not any(rm.role.name == "ADMIN" for rm in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized to heartbeat for this driver")
        
    await FleetService.send_heartbeat(db, id, org.id)
    return {"status": "online"}

@router.post("/drivers/{id}/location-stream")
async def stream_location(
    id: int,
    request: LocationStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.track"))
):
    """
    Ingests realtime GPS coordinates from the driver app.
    """
    org = get_user_org(db, current_user)
    if current_user.id != id and not any(rm.role.name == "ADMIN" for rm in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized to stream location for this driver")

    await FleetService.update_location(db, id, org.id, request.dict())
    return {"status": "ingested"}

@router.get("/live", response_model=FleetLiveResponse)
async def get_live_fleet(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns all active driver locations for the organization's map.
    """
    org = get_user_org(db, current_user)
    active_drivers = FleetRepository.get_active_fleet(db, org.id)
    return {
        "drivers": active_drivers,
        "total_online": len(active_drivers)
    }

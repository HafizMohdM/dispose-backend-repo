from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.map.map_schemas import LiveMapResponse, RouteResponse, MapEventResponse, MapEventCreate
from app.repositories.map_repo import MapRepository
from app.core.dependencies import get_user_org
from datetime import datetime
import json

router = APIRouter()

@router.get("/live", response_model=LiveMapResponse)
async def get_live_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns a unified snapshot of vehicles and pickups for the live dashboard map.
    """
    org = get_user_org(db, current_user)
    snapshot = MapRepository.get_live_map_snapshot(db, org.id)
    return {
        "vehicles": snapshot["vehicles"],
        "pickups": snapshot["pickups"],
        "timestamp": datetime.utcnow()
    }

@router.get("/routes/{driver_id}", response_model=RouteResponse)
async def get_driver_route(
    driver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns the active route (polyline) for a specific driver.
    """
    route = MapRepository.get_route_by_driver(db, driver_id)
    if not route:
        raise HTTPException(status_code=404, detail="No active route found for this driver")
    return route

@router.post("/events", response_model=MapEventResponse)
async def create_map_event(
    request: MapEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Logs an operational event on the map (e.g. Breakdown, Traffic).
    """
    org = get_user_org(db, current_user)
    from app.models.fleet import MapEvent
    event = MapEvent(
        organization_id=org.id,
        event_type=request.event_type,
        latitude=request.latitude,
        longitude=request.longitude,
        metadata_json=json.dumps(request.metadata) if request.metadata else None
    )
    new_event = MapRepository.create_map_event(db, event)
    db.commit()
    db.refresh(new_event)
    
    # Optional: Broadcast via WebSocket in next step
    return new_event

@router.get("/events", response_model=list[MapEventResponse])
async def get_map_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns active operational events for the map.
    """
    org = get_user_org(db, current_user)
    return MapRepository.get_active_events(db, org.id)

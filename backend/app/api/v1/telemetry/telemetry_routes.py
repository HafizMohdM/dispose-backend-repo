from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.websocket_manager import telemetry_ws_manager
from app.services.telemetry_ingest_service import TelemetryIngestService
from app.api.v1.telemetry.telemetry_schemas import TelemetryIngestPayload
from app.core.permissions import require_permission
from app.models.user import User
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def get_org_id(current_user: User) -> int:
    org_id = getattr(current_user, "current_org_id", getattr(current_user, "organization_id", None))
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context is required."
        )
    return org_id

@router.websocket("/stream")
async def telemetry_websocket_stream(websocket: WebSocket, token: str = Query(...)):
    """
    Stateful room-isolated WebSocket Broadcast Server.
    Authenticates via JWT token query parameter and binds client to org-scoped room.
    """
    try:
        payload = decode_access_token(token)
        org_id = payload.get("org_id")
        if not org_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await telemetry_ws_manager.connect(websocket, org_id)
    await telemetry_ws_manager.start_pubsub_listener()
    
    try:
        while True:
            # Prevent memory leaks by validating payload lengths & frame rates
            raw_data = await websocket.receive_text()
            
            # Enforce memory isolation and DDoS protection
            is_valid_frame = await telemetry_ws_manager.validate_and_track_frame(websocket, org_id, raw_data)
            if not is_valid_frame:
                await websocket.send_json({"error": "Payload too large or frame rate exceeded"})
                continue
                
    except WebSocketDisconnect:
        telemetry_ws_manager.disconnect(websocket, org_id)
    except Exception as e:
        logger.error(f"Error in WebSocket session: {e}")
        telemetry_ws_manager.disconnect(websocket, org_id)

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_telemetry_rest(
    payload: TelemetryIngestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    REST ingestion endpoint.
    Writes telemetry directly to isolated time-series table.
    """
    org_id = get_org_id(current_user)
    service = TelemetryIngestService(db)
    try:
        telemetry = service.ingest_telemetry(org_id, payload)
        return {"status": "success", "telemetry_id": str(telemetry.id)}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/drivers/{driver_id}/heartbeat", status_code=status.HTTP_200_OK)
def driver_heartbeat_fallback(
    driver_id: int,
    payload: TelemetryIngestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Lightweight REST endpoint fallback loop.
    Safely handles sub-second telemetry updates from systems without active WebSocket connections.
    """
    org_id = get_org_id(current_user)
    service = TelemetryIngestService(db)
    try:
        telemetry = service.ingest_telemetry(org_id, payload)
        return {
            "status": "success", 
            "driver_id": driver_id, 
            "telemetry_id": str(telemetry.id),
            "timestamp": telemetry.timestamp
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

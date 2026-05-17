from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.websocket.manager import manager
from app.services.analytics.analytics_service import AnalyticsService
from app.core.dependencies import get_user_org
import logging
import asyncio
import json

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_ws_user(token: str, db: Session):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except Exception:
        return None

@router.websocket("/ws/dashboard/live")
async def websocket_dashboard(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # 1. Authenticate
    user = await get_ws_user(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    # 2. Get Organization
    org = get_user_org(db, user)
    org_id = org.id if org else None
    
    if not org_id:
        await websocket.close(code=1008)
        return

    # 3. Connect to Manager
    await manager.connect(websocket, org_id)
    
    try:
        # 4. Push Initial Dashboard State (React-ready)
        # This gives the frontend the starting point for counters/charts
        dashboard_data = await AnalyticsService.get_executive_summary(db, org_id)
        await websocket.send_json({
            "event": "dashboard_init",
            "type": "analytics_update",
            "organization_id": org_id,
            "data": dashboard_data
        })

        # 5. Heartbeat loop
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id)
    except Exception as e:
        logger.error(f"Dashboard WebSocket error for Org {org_id}: {e}")
        manager.disconnect(websocket, org_id)

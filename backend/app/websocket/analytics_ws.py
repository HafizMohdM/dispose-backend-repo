from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.websocket.manager import manager
import logging
import asyncio

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

@router.websocket("/ws/analytics")
async def websocket_analytics(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # 1. Authenticate
    user = await get_ws_user(token, db)
    if not user:
        await websocket.close(code=1008) # Policy Violation
        return

    # 2. Get Organization (Assume user belongs to at least one)
    # This logic can be refined to support multi-org selection
    org_id = user.organization_id if hasattr(user, 'organization_id') else None
    if not org_id:
        # Fallback to checking OrganizationMember table if user model doesn't have org_id
        from app.models.organization_member import OrganizationMember
        member = db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id).first()
        org_id = member.organization_id if member else None

    if not org_id:
        await websocket.close(code=1008)
        return

    # 3. Connect
    await manager.connect(websocket, org_id)
    
    try:
        # 4. Keep-alive loop (Heartbeat)
        while True:
            # We don't expect data FROM the client for now, just keep connection open
            # and wait for disconnect
            data = await websocket.receive_text()
            # If client sends "ping", we send "pong"
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(websocket, org_id)

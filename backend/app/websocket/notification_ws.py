from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
import logging
import json

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.websocket.manager import manager
from app.core.dependencies import get_user_org
from app.services.notification_service import NotificationService
from app.utils.enums import NotificationStatus

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_ws_user(token: str, db: Session) -> Optional[User]:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except Exception:
        return None

@router.websocket("/live")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # 1. Authenticate WebSocket Connection
    user = await get_ws_user(token, db)
    if not user:
        logger.warning("Rejected WebSocket connection: Invalid token")
        await websocket.close(code=1008)  # Policy Violation
        return

    # 2. Get Scoped Tenant Organization
    try:
        org = get_user_org(db, user)
        org_id = org.id if org else None
    except Exception as e:
        logger.warning(f"Rejected WebSocket connection for User {user.id}: {e}")
        await websocket.close(code=1008)
        return

    if not org_id:
        logger.warning(f"Rejected WebSocket connection for User {user.id}: No organization mapped")
        await websocket.close(code=1008)
        return

    # 3. Join Connection Manager
    await manager.connect(websocket, org_id, user.id)

    try:
        # 4. Push Initial Unread Payload (Inbox & Count)
        service = NotificationService(db)
        unread_notifications = service.get_user_notifications(
            organization_id=org_id,
            user_id=user.id,
            status=NotificationStatus.UNREAD,
            archived=False,
            limit=50
        )
        unread_count = service.get_unread_count(
            organization_id=org_id,
            user_id=user.id,
            archived=False
        )

        serialized_notifications = []
        for n in unread_notifications:
            serialized_notifications.append({
                "id": str(n.id),
                "organization_id": n.organization_id,
                "user_id": n.user_id,
                "title": n.title,
                "message": n.message,
                "type": n.type.value if hasattr(n.type, "value") else str(n.type),
                "status": n.status.value if hasattr(n.status, "value") else str(n.status),
                "severity": n.severity.value if hasattr(n.severity, "value") else str(n.severity),
                "category": n.category.value if hasattr(n.category, "value") else str(n.category),
                "source_service": n.source_service,
                "archived": n.archived,
                "entity_type": n.entity_type,
                "entity_id": str(n.entity_id) if n.entity_id else None,
                "created_at": n.created_at.isoformat() if hasattr(n.created_at, "isoformat") else str(n.created_at),
                "read_at": n.read_at.isoformat() if n.read_at and hasattr(n.read_at, "isoformat") else None,
            })

        await websocket.send_json({
            "event": "notification_init",
            "data": {
                "notifications": serialized_notifications,
                "unread_count": unread_count
            }
        })

        # 5. Keep-Alive Ping-Pong Loop
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id, user.id)
    except Exception as e:
        logger.error(f"Error in notification websocket connection: {e}")
        manager.disconnect(websocket, org_id, user.id)

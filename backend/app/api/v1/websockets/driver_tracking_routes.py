import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.websockets.driver_tracking import manager

from app.services.driver_service import DriverService


router = APIRouter()


# Dispatcher dashboard connection
@router.websocket("/ws/dispatchers/{organization_id}")
async def dispatcher_ws(
    websocket: WebSocket,
    organization_id: int,
):

    await manager.connect_dispatcher(
        organization_id,
        websocket,
    )

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_dispatcher(
            organization_id,
            websocket,
        )


# Driver sends location
@router.websocket("/ws/drivers/{driver_id}/{organization_id}")
async def driver_ws(
    websocket: WebSocket,
    driver_id: str,
    organization_id: int,
    db: Session = Depends(get_db),
):

    await manager.connect_driver(
        driver_id,
        websocket,
    )

    driver_service = DriverService(db)

    try:
        while True:

            data = await websocket.receive_text()

            location = json.loads(data)

            lat = location["lat"]
            lng = location["lng"]

            # Save to database using your existing logic
            driver_service.update_driver_location(
                driver_id=driver_id,
                latitude=lat,
                longitude=lng,
            )

            # Broadcast to dispatchers
            await manager.broadcast_location(
                organization_id,
                {
                    "driver_id": driver_id,
                    "lat": lat,
                    "lng": lng,
                },
            )

    except WebSocketDisconnect:
        manager.disconnect_driver(driver_id)
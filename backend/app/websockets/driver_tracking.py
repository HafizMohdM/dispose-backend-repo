import json
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect


class DriverTrackingManager:

    def __init__(self):
        self.dispatchers: Dict[int, List[WebSocket]] = {}
        self.drivers: Dict[str, WebSocket] = {}

    async def connect_driver(
        self,
        driver_id: str,
        websocket: WebSocket,
    ):
        await websocket.accept()
        self.drivers[driver_id] = websocket

    def disconnect_driver(
        self,
        driver_id: str,
    ):
        if driver_id in self.drivers:
            del self.drivers[driver_id]

    async def connect_dispatcher(
        self,
        organization_id: int,
        websocket: WebSocket,
    ):
        await websocket.accept()
        if organization_id not in self.dispatchers:
            self.dispatchers[organization_id] = []
        self.dispatchers[organization_id].append(websocket)

    def disconnect_dispatcher(
        self,
        organization_id: int,
        websocket: WebSocket,
    ):
        if organization_id in self.dispatchers:
            if websocket in self.dispatchers[organization_id]:
                self.dispatchers[organization_id].remove(websocket)
            if not self.dispatchers[organization_id]:
                del self.dispatchers[organization_id]

    async def broadcast_location(
        self,
        organization_id: int,
        location_data: dict,
    ):
        if organization_id not in self.dispatchers:
            return
        message = json.dumps(location_data)

        for dispatcher in self.dispatchers[organization_id]:
            try:
                await dispatcher.send_text(message)
            except Exception:
                pass

manager = DriverTrackingManager()
    
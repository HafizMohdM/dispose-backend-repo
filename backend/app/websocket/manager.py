from fastapi import WebSocket
from typing import Dict, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # active_connections: {org_id: [WebSocket, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, org_id: int):
        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        self.active_connections[org_id].append(websocket)
        logger.info(f"WebSocket connected for Org {org_id}. Total connections for org: {len(self.active_connections[org_id])}")

    def disconnect(self, websocket: WebSocket, org_id: int):
        if org_id in self.active_connections:
            if websocket in self.active_connections[org_id]:
                self.active_connections[org_id].remove(websocket)
                if not self.active_connections[org_id]:
                    del self.active_connections[org_id]
        logger.info(f"WebSocket disconnected for Org {org_id}")

    async def broadcast_to_org(self, org_id: int, message: dict):
        """Send message to all connected clients in a specific organization"""
        if org_id in self.active_connections:
            disconnected_sockets = []
            for connection in self.active_connections[org_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to WebSocket for Org {org_id}: {e}")
                    disconnected_sockets.append(connection)
            
            # Cleanup broken connections
            for socket in disconnected_sockets:
                self.disconnect(socket, org_id)

    async def broadcast_global(self, message: dict):
        """Send message to all connected clients across all organizations (SuperAdmin only)"""
        for org_id in list(self.active_connections.keys()):
            await self.broadcast_to_org(org_id, message)

# Global connection manager instance
manager = ConnectionManager()

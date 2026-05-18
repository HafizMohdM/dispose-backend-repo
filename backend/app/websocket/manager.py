from fastapi import WebSocket
from typing import Dict, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # active_connections: {org_id: [WebSocket, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # active_user_connections: {user_id: [WebSocket, ...]}
        self.active_user_connections: Dict[int, List[WebSocket]] = {}
        # socket_metadata: {WebSocket: (org_id, user_id)}
        self.socket_metadata: Dict[WebSocket, tuple] = {}

    async def connect(self, websocket: WebSocket, org_id: int, user_id: Optional[int] = None):
        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        self.active_connections[org_id].append(websocket)
        
        if user_id is not None:
            if user_id not in self.active_user_connections:
                self.active_user_connections[user_id] = []
            self.active_user_connections[user_id].append(websocket)
            
        self.socket_metadata[websocket] = (org_id, user_id)
        logger.info(f"WebSocket connected for Org {org_id}, User {user_id}. Total connections for org: {len(self.active_connections[org_id])}")

    def disconnect_socket(self, websocket: WebSocket):
        if websocket in self.socket_metadata:
            org_id, user_id = self.socket_metadata.pop(websocket)
            if org_id in self.active_connections:
                if websocket in self.active_connections[org_id]:
                    self.active_connections[org_id].remove(websocket)
                    if not self.active_connections[org_id]:
                        del self.active_connections[org_id]
            if user_id is not None and user_id in self.active_user_connections:
                if websocket in self.active_user_connections[user_id]:
                    self.active_user_connections[user_id].remove(websocket)
                    if not self.active_user_connections[user_id]:
                        del self.active_user_connections[user_id]
            logger.info(f"WebSocket disconnected for Org {org_id}, User {user_id}")
        else:
            # Fallback scan
            for org_id, sockets in list(self.active_connections.items()):
                if websocket in sockets:
                    sockets.remove(websocket)
                    if not sockets:
                        del self.active_connections[org_id]
            for user_id, sockets in list(self.active_user_connections.items()):
                if websocket in sockets:
                    sockets.remove(websocket)
                    if not sockets:
                        del self.active_user_connections[user_id]

    def disconnect(self, websocket: WebSocket, org_id: int, user_id: Optional[int] = None):
        """Backward compatible disconnect method"""
        self.disconnect_socket(websocket)

    async def send_to_user(self, user_id: int, message: dict):
        """Send message directly to all connected sockets of a specific user"""
        if user_id in self.active_user_connections:
            disconnected_sockets = []
            for connection in self.active_user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message to User {user_id}: {e}")
                    disconnected_sockets.append(connection)
            
            # Clean up dead sockets
            for socket in disconnected_sockets:
                self.disconnect_socket(socket)

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
                self.disconnect_socket(socket)

    async def broadcast_global(self, message: dict):
        """Send message to all connected clients across all organizations (SuperAdmin only)"""
        for org_id in list(self.active_connections.keys()):
            await self.broadcast_to_org(org_id, message)

# Global connection manager instance
manager = ConnectionManager()

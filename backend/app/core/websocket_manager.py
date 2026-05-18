from fastapi import WebSocket
from typing import Dict, List, Optional
import logging
import json
from app.core.config import REDIS_URL
import redis.asyncio as redis
import asyncio

logger = logging.getLogger(__name__)

class MemoryIsolatedWebSocketManager:
    """
    Stateful room-isolated WebSocket Broadcast Server.
    Enforces payload limits, frame tracking, and memory isolation.
    """
    def __init__(self, max_payload_bytes: int = 4096, max_frames_per_minute: int = 120):
        # tenant-locked rooms: {org_id: {websocket: metadata}}
        self.active_rooms: Dict[int, Dict[WebSocket, dict]] = {}
        self.max_payload_bytes = max_payload_bytes
        self.max_frames_per_minute = max_frames_per_minute
        
        # Redis connection for pub/sub scaling
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.pubsub_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, org_id: int):
        await websocket.accept()
        if org_id not in self.active_rooms:
            self.active_rooms[org_id] = {}
        
        # Track frame counts and timestamps for rate limiting/memory isolation
        self.active_rooms[org_id][websocket] = {
            "connected_at": asyncio.get_event_loop().time(),
            "frame_timestamps": []
        }
        logger.info(f"WebSocket connected for Tenant Room {org_id}. Total room connections: {len(self.active_rooms[org_id])}")

    def disconnect(self, websocket: WebSocket, org_id: int):
        if org_id in self.active_rooms:
            if websocket in self.active_rooms[org_id]:
                del self.active_rooms[org_id][websocket]
                if not self.active_rooms[org_id]:
                    del self.active_rooms[org_id]
        logger.info(f"WebSocket disconnected from Tenant Room {org_id}")

    async def validate_and_track_frame(self, websocket: WebSocket, org_id: int, raw_payload: str) -> bool:
        """
        Memory Isolation & Hard Ingestion Limits.
        Validates payload length, total frames, and frequency tracking to block DDoS or memory leaks.
        """
        # 1. Payload size check
        if len(raw_payload.encode('utf-8')) > self.max_payload_bytes:
            logger.warning(f"WebSocket payload rejected from Room {org_id}: Exceeded size limit.")
            return False

        # 2. Rate limit frame tracking
        now = asyncio.get_event_loop().time()
        room = self.active_rooms.get(org_id, {})
        conn_meta = room.get(websocket)
        if not conn_meta:
            return False
            
        timestamps = conn_meta["frame_timestamps"]
        # Keep only timestamps within last 60 seconds
        timestamps = [ts for ts in timestamps if now - ts < 60]
        timestamps.append(now)
        conn_meta["frame_timestamps"] = timestamps
        
        if len(timestamps) > self.max_frames_per_minute:
            logger.warning(f"WebSocket frame rate limit exceeded in Room {org_id}.")
            return False
            
        return True

    async def publish_to_room(self, org_id: int, message: dict):
        """Publish room update through Redis Pub/Sub so all app instances broadcast it"""
        channel = f"telemetry:room_{org_id}"
        await self.redis_client.publish(channel, json.dumps(message, default=str))

    async def start_pubsub_listener(self):
        """Starts background listener to consume Redis channels and push to connected WebSockets in parallel instances"""
        if self.pubsub_task and not self.pubsub_task.done():
            return
            
        async def listen():
            try:
                await self.pubsub.psubscribe("telemetry:room_*")
                async for message in self.pubsub.listen():
                    if message["type"] == "pmessage":
                        channel = message["channel"]
                        org_id = int(channel.split("_")[-1])
                        data = json.loads(message["data"])
                        await self.broadcast_to_room_local(org_id, data)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in telemetry pubsub listener: {e}")
                
        self.pubsub_task = asyncio.create_task(listen())

    async def broadcast_to_room_local(self, org_id: int, message: dict):
        """Directly sends a payload to all local WebSockets joined to this room"""
        room = self.active_rooms.get(org_id, {})
        disconnected_sockets = []
        for socket in list(room.keys()):
            try:
                await socket.send_json(message)
            except Exception as e:
                logger.error(f"Failed local broadcast in Room {org_id}: {e}")
                disconnected_sockets.append(socket)
                
        for socket in disconnected_sockets:
            self.disconnect(socket, org_id)

# Global room-isolated manager
telemetry_ws_manager = MemoryIsolatedWebSocketManager()

import json
import asyncio
import logging
import redis.asyncio as redis
from app.core.config import REDIS_URL
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

class PubSubManager:
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.is_listening = False

    async def publish(self, channel: str, message: dict):
        """Publish an event to a Redis channel"""
        try:
            await self.redis_client.publish(channel, json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Failed to publish to Redis channel {channel}: {e}")

    async def start_listener(self):
        """Background task to listen for Redis messages and broadcast them to WebSockets"""
        if self.is_listening:
            return
        
        self.is_listening = True
        logger.info("Starting Redis Pub/Sub Listener...")
        
        while self.is_listening:
            try:
                # Re-subscribe on each retry if needed
                await self.pubsub.psubscribe("analytics:*", "dashboard:*")
                
                async for message in self.pubsub.listen():
                    if not self.is_listening:
                        break

                    if message["type"] == "pmessage":
                        channel = message["channel"]
                        data = json.loads(message["data"])
                        
                        org_id = data.get("organization_id")
                        
                        if org_id:
                            await manager.broadcast_to_org(org_id, data)
                        elif channel in ["analytics:global", "dashboard:global"]:
                            await manager.broadcast_global(data)
                            
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.error(f"Redis Pub/Sub connection lost. Retrying in 5 seconds... Error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in Redis Pub/Sub Listener: {e}")
                await asyncio.sleep(5)

    async def stop_listener(self):
        """Safely stop the listener without crashing during shutdown"""
        self.is_listening = False
        try:
            # We use a timeout to avoid hanging if Redis is dead
            await asyncio.wait_for(self.pubsub.punsubscribe("analytics:*", "dashboard:*"), timeout=2.0)
        except Exception as e:
            logger.warning(f"Could not unsubscribe from Redis during shutdown: {e}")
        logger.info("Stopped Redis Pub/Sub Listener")


# Global PubSub instance
pubsub_service = PubSubManager()

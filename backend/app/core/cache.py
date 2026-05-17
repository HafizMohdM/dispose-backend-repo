import json
import functools
from typing import Optional, Any, Callable
from datetime import timedelta
import logging
import redis.asyncio as redis
from app.core.config import REDIS_URL

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[redis.Redis] = None

async def init_redis():
    global redis_client
    try:
        # Resolve 'localhost' specifically to 127.0.0.1 if needed, but standard REDIS_URL should work.
        # Adding socket_connect_timeout to fail fast if Redis is down.
        redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        await redis_client.ping()
        logger.info(f"Successfully connected to Redis at {REDIS_URL}")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to connect to Redis at {REDIS_URL}. Error: {e}")
        # Ensure redis_client is set to None so the application can run in 'degraded' mode
        redis_client = None

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

def cached(ttl: int = 300, prefix: str = "analytics"):
    """
    Decorator to cache FastAPI route responses in Redis.
    Supports organization-scoped isolation.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_client:
                return await func(*args, **kwargs)

            # Generate cache key based on function name, organization_id, and query params
            org_id = kwargs.get("org_id") or kwargs.get("organization_id")
            # If org_id is not in kwargs, try to get it from current_user or similar if needed
            # For simplicity, we assume org_id is passed to the service/repo method
            
            key_parts = [prefix, func.__name__]
            if org_id:
                key_parts.append(str(org_id))
            
            # Add other relevant kwargs to key
            for k, v in sorted(kwargs.items()):
                if k not in ["db", "current_user", "org_id", "organization_id"]:
                    key_parts.append(f"{k}:{v}")

            cache_key = ":".join(key_parts)

            try:
                # Try to get from cache
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Error reading from cache: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            try:
                # Save to cache
                if result is not None:
                    await redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                    logger.debug(f"Cache stored for key: {cache_key}")
            except Exception as e:
                logger.warning(f"Error writing to cache: {e}")

            return result
        return wrapper
    return decorator

async def invalidate_cache(pattern: str):
    """Invalidate all keys matching the pattern"""
    if not redis_client:
        return
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")

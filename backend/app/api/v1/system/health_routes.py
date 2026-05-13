from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.cache import redis_client
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def basic_health():
    """
    Returns 200 if the FastAPI application is responding.
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "dispose-backend"
    }

@router.get("/database")
async def db_health(db: Session = Depends(get_db)):
    """
    Probes the PostgreSQL connection.
    """
    try:
        start_time = time.time()
        db.execute(text("SELECT 1"))
        latency = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "connection": "verified"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@router.get("/redis")
async def redis_health():
    """
    Probes the Redis connection.
    """
    if not redis_client:
        return {"status": "unhealthy", "error": "Redis client not initialized"}
    try:
        start_time = time.time()
        await redis_client.ping()
        latency = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "connection": "verified"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@router.get("/celery")
async def celery_health():
    """
    Checks the status of the Celery worker pool.
    """
    try:
        from app.core.celery_app import celery_app
        # This checks if there are active workers registered
        i = celery_app.control.inspect()
        stats = i.stats()
        if not stats:
            return {"status": "degraded", "error": "No active workers detected"}
        return {
            "status": "healthy",
            "workers_online": len(stats),
            "details": stats
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.get("/websocket")
async def websocket_health():
    """
    Returns metrics from the WebSocket ConnectionManager.
    """
    from app.websocket.manager import manager
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    total_orgs = len(manager.active_connections)
    return {
        "status": "healthy",
        "active_connections": total_connections,
        "active_organizations": total_orgs
    }

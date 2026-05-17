import json
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.cache import redis_client
from app.models.analytics import AnalyticsEvent, EventType
from app.websocket.manager import manager
import logging

logger = logging.getLogger(__name__)

class EventPublisher:
    """
    Central event dispatcher for the application.
    Implements a write-aside pattern: DB (Log) + Redis (Cache/Counters).
    """

    @staticmethod
    async def publish(
        db: Session,
        event_type: EventType,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        try:
            # 1. Persist to PostgreSQL (Immutable Log)
            event = AnalyticsEvent(
                organization_id=organization_id,
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                event_metadata=metadata or {}
            )
            db.add(event)
            # We don't commit here; we assume the caller is in a transaction

            # 2. Update Real-time Counters in Redis
            if organization_id:
                await EventPublisher._update_redis_counters(organization_id, event_type, metadata)

            # 3. Broadcast via WebSockets for live dashboard updates
            if organization_id:
                await manager.broadcast_to_org(organization_id, {
                    "type": "analytics_event",
                    "event": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": metadata
                })

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {str(e)}")

    @staticmethod
    async def _update_redis_counters(org_id: int, event_type: EventType, metadata: Optional[Dict[str, Any]]):
        """
        Atomic increments in Redis for ultra-fast KPI retrieval.
        """
        if not redis_client:
            return

        today = datetime.utcnow().strftime("%Y-%m-%d")
        base_key = f"org:{org_id}:analytics:{today}"

        # Increment specific counters based on event type
        if event_type == EventType.PICKUP_CREATED:
            await redis_client.hincrby(base_key, "total_pickups", 1)
        
        elif event_type == EventType.PICKUP_COMPLETED:
            await redis_client.hincrby(base_key, "completed_pickups", 1)
            # If weight is provided in metadata, increment waste counter
            if metadata and "weight_kg" in metadata:
                weight = int(metadata["weight_kg"])
                await redis_client.hincrby(base_key, "total_waste_kg", weight)
                
                # Approximate CO2 saved (Example: 1kg waste = 0.5kg CO2 saved)
                co2_saved = int(weight * 0.5)
                await redis_client.hincrby(base_key, "total_co2_saved_kg", co2_saved)

        elif event_type == EventType.PAYMENT_SUCCESS:
            if metadata and "amount" in metadata:
                amount_cents = int(float(metadata["amount"]) * 100)
                await redis_client.hincrby(base_key, "total_revenue_cents", amount_cents)

        # Set expiry for the daily key (keep for 48h for trend overlap)
        await redis_client.expire(base_key, 172800)

import json
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.cache import redis_client
from app.models.analytics import AnalyticsEvent, EventType
from app.websocket.manager import manager
from app.utils.enums import NotificationSeverity, NotificationCategory
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

            # 4. Integrate Real-time Notifications for Core SaaS Events
            notification_map = {
                EventType.PICKUP_CREATED: {
                    "title": "New Pickup Scheduled",
                    "message": "A new waste pickup request has been scheduled successfully.",
                    "category": NotificationCategory.OPERATIONAL,
                    "severity": NotificationSeverity.INFO,
                },
                EventType.PICKUP_COMPLETED: {
                    "title": "Pickup Completed Successfully",
                    "message": "Your scheduled waste pickup request has been successfully completed.",
                    "category": NotificationCategory.OPERATIONAL,
                    "severity": NotificationSeverity.SUCCESS,
                },
                EventType.PAYMENT_SUCCESS: {
                    "title": "Invoice Payment Captured",
                    "message": f"Payment of INR {metadata.get('amount', '0.0') if metadata else '0.0'} captured successfully.",
                    "category": NotificationCategory.ALERT,
                    "severity": NotificationSeverity.SUCCESS,
                },
                EventType.PAYMENT_FAILED: {
                    "title": "Invoice Payment Authorization Failed",
                    "message": "A payment renewal attempt failed. Please check your payment methods immediately.",
                    "category": NotificationCategory.ALERT,
                    "severity": NotificationSeverity.CRITICAL,
                },
                EventType.SUB_UPGRADED: {
                    "title": "Subscription Plan Upgraded",
                    "message": "Your organization subscription has been successfully upgraded to the new plan.",
                    "category": NotificationCategory.ALERT,
                    "severity": NotificationSeverity.SUCCESS,
                }
            }

            if event_type in notification_map and organization_id and user_id:
                notif_data = notification_map[event_type]
                
                # Check for dynamic override in metadata if provided
                title = metadata.get("title", notif_data["title"]) if metadata else notif_data["title"]
                message = metadata.get("message", notif_data["message"]) if metadata else notif_data["message"]
                
                parsed_entity_id = None
                if entity_id:
                    try:
                        from uuid import UUID
                        parsed_entity_id = UUID(str(entity_id))
                    except Exception:
                        pass
                
                from app.models.notification import Notification
                from app.utils.enums import NotificationStatus
                
                new_notif = Notification(
                    organization_id=organization_id,
                    user_id=user_id,
                    title=title,
                    message=message,
                    type="SYSTEM",
                    status=NotificationStatus.UNREAD,
                    severity=notif_data["severity"],
                    category=notif_data["category"],
                    source_service="EVENT_DISPATCHER",
                    archived=False,
                    entity_type=entity_type,
                    entity_id=parsed_entity_id
                )
                db.add(new_notif)
                db.flush()
                
                # Publish the created notification via Redis PubSub for real-time WebSocket delivery
                from app.core.pubsub import pubsub_service
                
                # Query updated unread count
                from app.services.notification_service import NotificationService
                service = NotificationService(db)
                unread_count = service.get_unread_count(organization_id, user_id)
                
                await pubsub_service.publish(f"notifications:user_{user_id}", {
                    "event": "notification_new",
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "data": {
                        "notification": {
                            "id": str(new_notif.id),
                            "organization_id": new_notif.organization_id,
                            "user_id": new_notif.user_id,
                            "title": new_notif.title,
                            "message": new_notif.message,
                            "type": "SYSTEM",
                            "status": "UNREAD",
                            "severity": new_notif.severity.value,
                            "category": new_notif.category.value,
                            "source_service": new_notif.source_service,
                            "archived": False,
                            "entity_type": new_notif.entity_type,
                            "entity_id": str(new_notif.entity_id) if new_notif.entity_id else None,
                            "created_at": new_notif.created_at.isoformat() if hasattr(new_notif.created_at, "isoformat") else str(new_notif.created_at),
                            "read_at": None,
                        },
                        "unread_count": unread_count
                    }
                })
                
                # Trigger multi-channel delivery (Email + Push) via Celery
                try:
                    from app.tasks.notification_tasks import dispatch_multi_channel
                    dispatch_multi_channel.delay(
                        str(new_notif.id),
                        user_id,
                        organization_id,
                    )
                except Exception as dispatch_err:
                    logger.warning(f"Multi-channel dispatch queuing failed (non-blocking): {dispatch_err}")

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

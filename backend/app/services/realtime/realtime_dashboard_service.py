from sqlalchemy.orm import Session
from app.services.analytics.analytics_service import AnalyticsService
from app.core.pubsub import pubsub_service
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class RealtimeDashboardService:
    @staticmethod
    async def broadcast_kpi_update(db: Session, org_id: int):
        """
        Fetches latest KPI summary and broadcasts it to the dashboard.
        """
        try:
            # 1. Fetch current analytics summary
            dashboard_data = await AnalyticsService.get_dashboard_summary(db, org_id)
            
            # 2. Publish to Redis dashboard channel
            await pubsub_service.publish(
                f"dashboard_org_{org_id}",
                {
                    "event": "dashboard_kpi_update",
                    "organization_id": org_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": dashboard_data
                }
            )
            logger.info(f"Broadcasted realtime KPI update for Org {org_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast KPI update for Org {org_id}: {e}")

    @staticmethod
    async def broadcast_activity(org_id: int, activity_type: str, message: str, data: dict = None):
        """
        Broadcasts a live activity feed item.
        """
        await pubsub_service.publish(
            f"dashboard_org_{org_id}",
            {
                "event": "dashboard_activity",
                "organization_id": org_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "type": activity_type,
                    "message": message,
                    "meta": data or {}
                }
            }
        )

# Throttler to prevent overwhelming Redis/Clients with too many updates
class UpdateThrottler:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.pending_orgs = set()
        self.lock = asyncio.Lock()

    async def trigger_update(self, db: Session, org_id: int):
        async with self.lock:
            if org_id in self.pending_orgs:
                return
            self.pending_orgs.add(org_id)
        
        # Wait for the interval before processing to batch updates
        await asyncio.sleep(self.interval)
        
        try:
            await RealtimeDashboardService.broadcast_kpi_update(db, org_id)
        finally:
            async with self.lock:
                self.pending_orgs.remove(org_id)

dashboard_throttler = UpdateThrottler(interval=1.0)

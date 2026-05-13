from sqlalchemy.orm import Session
from app.repositories.fleet_repo import FleetRepository
from app.models.fleet import GPSHistory
from app.core.pubsub import pubsub_service
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class FleetService:
    
    @staticmethod
    async def update_location(db: Session, driver_id: int, org_id: int, data: dict):
        # 1. Update Live Location (UPSERT)
        location_payload = {
            "driver_id": driver_id,
            "organization_id": org_id,
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "speed": data.get("speed", 0.0),
            "heading": data.get("heading", 0.0)
        }
        FleetRepository.update_live_location(db, location_payload)

        # 2. Log to History
        history = GPSHistory(
            driver_id=driver_id,
            organization_id=org_id,
            latitude=data["latitude"],
            longitude=data["longitude"],
            speed=data.get("speed", 0.0),
            heading=data.get("heading", 0.0),
            accuracy=data.get("accuracy", 0.0)
        )
        FleetRepository.create_gps_history(db, history)
        
        db.commit()

        # 3. Broadcast Realtime Event
        asyncio.create_task(pubsub_service.publish(
            f"fleet:org_{org_id}",
            {
                "event": "driver_moved",
                "organization_id": org_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "driver_id": driver_id,
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "speed": data.get("speed", 0.0),
                    "heading": data.get("heading", 0.0)
                }
            }
        ))

    @staticmethod
    async def send_heartbeat(db: Session, driver_id: int, org_id: int):
        # Ensure session exists or start one
        # For now, just update the live location timestamp to keep "online" status
        FleetRepository.update_live_location(db, {
            "driver_id": driver_id,
            "organization_id": org_id,
            "updated_at": datetime.utcnow()
        })
        db.commit()
        
        # Broadcast status
        asyncio.create_task(pubsub_service.publish(
            f"fleet:org_{org_id}",
            {
                "event": "driver_online",
                "organization_id": org_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"driver_id": driver_id}
            }
        ))

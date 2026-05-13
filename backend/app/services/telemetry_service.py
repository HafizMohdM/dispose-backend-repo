from sqlalchemy.orm import Session
from app.repositories.telemetry_repo import TelemetryRepository
from app.models.telemetry import TelemetryEvent, VehicleDiagnostic
from app.core.pubsub import pubsub_service
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class TelemetryService:
    
    @staticmethod
    async def ingest_data(db: Session, device_id: int, vehicle_id: int, org_id: int, data: dict):
        # 1. Store Raw Telemetry Event
        event = TelemetryEvent(
            vehicle_id=vehicle_id,
            organization_id=org_id,
            event_type=data.get("type", "diagnostic"),
            telemetry_data=data
        )
        TelemetryRepository.create_telemetry_event(db, event)

        # 2. Update Vehicle Diagnostic Snapshot
        # If the data contains health metrics, update the snapshot
        if "engine_health" in data or "fuel_level" in data:
            diag = VehicleDiagnostic(
                vehicle_id=vehicle_id,
                engine_health=data.get("engine_health", "ok"),
                battery_status=data.get("battery_status", "good"),
                fuel_level=data.get("fuel_level", 100),
                temperature=data.get("temperature"),
                diagnostic_code=data.get("diagnostic_code")
            )
            TelemetryRepository.create_diagnostic_snapshot(db, diag)
        
        db.commit()

        # 3. Broadcast Realtime Telemetry
        asyncio.create_task(pubsub_service.publish(
            f"telemetry:vehicle_{vehicle_id}",
            {
                "event": "telemetry_update",
                "vehicle_id": vehicle_id,
                "organization_id": org_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
        ))
        
        # Also broadcast to org-level fleet channel for dashboard gauges
        asyncio.create_task(pubsub_service.publish(
            f"fleet:org_{org_id}",
            {
                "event": "vehicle_health_update",
                "vehicle_id": vehicle_id,
                "data": {
                    "fuel": data.get("fuel_level"),
                    "engine": data.get("engine_health"),
                    "temp": data.get("temperature")
                }
            }
        ))

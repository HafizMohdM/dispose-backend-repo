import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from uuid import UUID

from app.models.telemetry import VehicleTelemetry
from app.api.v1.telemetry.telemetry_schemas import TelemetryIngestRequest
from app.repositories.telemetry_repo import TelemetryRepository
from app.core.pubsub import pubsub_service

logger = logging.getLogger(__name__)

class TelemetryService:
    def __init__(self, db: Session):
        self.db = db
        self.telemetry_repo = TelemetryRepository(db)

    async def ingest_telemetry(self, vehicle_id: UUID, organization_id: int, payload: TelemetryIngestRequest) -> VehicleTelemetry:
        telemetry = VehicleTelemetry(
            organization_id=organization_id,
            vehicle_id=vehicle_id,
            speed_kmh=payload.speed_kmh,
            fuel_level_percentage=payload.fuel_level_percentage,
            battery_voltage=payload.battery_voltage,
            ignition_state=payload.ignition_state,
            timestamp=payload.timestamp
        )

        try:
            inserted_telemetry = self.telemetry_repo.insert(telemetry)
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError during telemetry ingestion: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle not found or constraint violation."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error during telemetry ingestion: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while saving telemetry."
            )

        # Publish state propagation
        pubsub_payload = {
            "type": "telemetry_update",
            "organization_id": organization_id,
            "vehicle_id": str(vehicle_id),
            "telemetry": {
                "id": str(inserted_telemetry.id),
                "speed_kmh": inserted_telemetry.speed_kmh,
                "fuel_level_percentage": inserted_telemetry.fuel_level_percentage,
                "battery_voltage": inserted_telemetry.battery_voltage,
                "ignition_state": inserted_telemetry.ignition_state,
                "timestamp": inserted_telemetry.timestamp.isoformat()
            }
        }

        try:
            # publish the payload via existing pubsub_service
            await pubsub_service.publish(channel=f"org_{organization_id}", message=pubsub_payload)
        except Exception as e:
            logger.warning(f"Failed to publish telemetry to pubsub: {e}")

        return inserted_telemetry

    def get_latest_telemetry(self, vehicle_id: UUID, organization_id: int) -> VehicleTelemetry:
        telemetry = self.telemetry_repo.get_latest_for_vehicle(vehicle_id, organization_id)
        if not telemetry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No telemetry data found for this vehicle."
            )
        return telemetry

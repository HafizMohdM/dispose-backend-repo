from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
from app.models.telemetry import VehicleTelemetry
from app.models.vehicle import Vehicle
from app.models.fleet import GPSHistory
from app.repositories.fleet_repo import FleetRepository
from app.repositories.vehicle_repo import VehicleRepository
from app.core.websocket_manager import telemetry_ws_manager
from app.api.v1.telemetry.telemetry_schemas import TelemetryIngestPayload

class TelemetryIngestService:
    def __init__(self, db: Session):
        self.db = db
        self.fleet_repo = FleetRepository(db)
        self.vehicle_repo = VehicleRepository(db)

    def ingest_telemetry(self, org_id: int, payload: TelemetryIngestPayload) -> VehicleTelemetry:
        """
        Relational I/O Decoupling:
        Writes telemetry directly to the isolated time-series table.
        Does not issue lock contention updates on the main Vehicle table.
        """
        # Validate Vehicle exists and belongs to the org
        vehicle = self.db.query(Vehicle).filter(
            Vehicle.id == payload.vehicle_id,
            Vehicle.organization_id == org_id
        ).first()
        if not vehicle:
            raise ValueError("Vehicle not found or does not belong to organization.")
            
        # Create Time-Series Record
        telemetry = VehicleTelemetry(
            organization_id=org_id,
            vehicle_id=payload.vehicle_id,
            speed_kmh=payload.speed_kmh,
            fuel_level_percentage=payload.fuel_level_percentage,
            battery_voltage=payload.battery_voltage,
            ignition_state=payload.ignition_state,
            timestamp=datetime.utcnow()
        )
        self.db.add(telemetry)
        
        # Check active driver mapping for GPS/Map update
        assignment = self.vehicle_repo.get_active_assignment(payload.vehicle_id)
        if assignment:
            # Update Live Location in GPS space
            location_payload = {
                "driver_id": assignment.driver_id,
                "organization_id": org_id,
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "speed": payload.speed or (payload.speed_kmh / 3.6), # convert to m/s
                "heading": payload.heading or 0.0
            }
            self.fleet_repo.update_live_location(self.db, location_payload)
            
            # Log GPS History
            history = GPSHistory(
                driver_id=assignment.driver_id,
                organization_id=org_id,
                latitude=payload.latitude,
                longitude=payload.longitude,
                speed=payload.speed or (payload.speed_kmh / 3.6),
                heading=payload.heading or 0.0
            )
            self.fleet_repo.create_gps_history(self.db, history)

        # Commit high-frequency transaction immediately to minimize lock holding times
        self.db.commit()
        
        # Broadcast coordinate stream
        broadcast_payload = {
            "event": "vehicle_telemetry",
            "vehicle_id": payload.vehicle_id,
            "organization_id": org_id,
            "speed_kmh": payload.speed_kmh,
            "fuel_level_percentage": payload.fuel_level_percentage,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        asyncio.create_task(telemetry_ws_manager.publish_to_room(org_id, broadcast_payload))
        
        return telemetry

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.telemetry import VehicleTelemetry

class TelemetryRepository:
    def __init__(self, db: Session):
        self.db = db

    def insert(self, telemetry: VehicleTelemetry) -> VehicleTelemetry:
        self.db.add(telemetry)
        self.db.commit()
        self.db.refresh(telemetry)
        return telemetry

    def get_latest_for_vehicle(self, vehicle_id: UUID, organization_id: int) -> Optional[VehicleTelemetry]:
        return self.db.query(VehicleTelemetry).filter(
            VehicleTelemetry.vehicle_id == vehicle_id,
            VehicleTelemetry.organization_id == organization_id
        ).order_by(VehicleTelemetry.timestamp.desc()).first()

    def get_history_for_vehicle(
        self, vehicle_id: UUID, organization_id: int, limit: int = 100
    ) -> List[VehicleTelemetry]:
        return self.db.query(VehicleTelemetry).filter(
            VehicleTelemetry.vehicle_id == vehicle_id,
            VehicleTelemetry.organization_id == organization_id
        ).order_by(VehicleTelemetry.timestamp.desc()).limit(limit).all()

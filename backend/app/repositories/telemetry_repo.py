from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.telemetry import TelemetryEvent, SensorStream, VehicleDiagnostic, IOTDevice
from typing import List, Optional

class TelemetryRepository:
    
    @staticmethod
    def create_telemetry_event(db: Session, event: TelemetryEvent) -> TelemetryEvent:
        db.add(event)
        return event

    @staticmethod
    def get_latest_diagnostics(db: Session, vehicle_id: int) -> Optional[VehicleDiagnostic]:
        return db.query(VehicleDiagnostic).filter(
            VehicleDiagnostic.vehicle_id == vehicle_id
        ).order_by(VehicleDiagnostic.created_at.desc()).first()

    @staticmethod
    def get_sensor_history(db: Session, device_id: int, sensor_type: str, limit: int = 100) -> List[SensorStream]:
        return db.query(SensorStream).filter(
            and_(SensorStream.device_id == device_id, SensorStream.sensor_type == sensor_type)
        ).order_by(SensorStream.recorded_at.desc()).limit(limit).all()

    @staticmethod
    def create_diagnostic_snapshot(db: Session, diag: VehicleDiagnostic) -> VehicleDiagnostic:
        db.add(diag)
        return diag

    @staticmethod
    def get_device_by_identifier(db: Session, identifier: str) -> Optional[IOTDevice]:
        return db.query(IOTDevice).filter(IOTDevice.device_identifier == identifier).first()

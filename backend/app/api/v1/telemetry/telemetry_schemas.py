from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Any

class TelemetryIngestRequest(BaseModel):
    device_identifier: str
    type: str # diagnostic, health, alert
    engine_health: Optional[str] = "ok"
    battery_status: Optional[str] = "good"
    fuel_level: Optional[int] = 100
    temperature: Optional[float] = None
    diagnostic_code: Optional[str] = None
    additional_data: Optional[dict] = None

class DiagnosticResponse(BaseModel):
    vehicle_id: int
    engine_health: str
    battery_status: str
    fuel_level: int
    temperature: Optional[float]
    diagnostic_code: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class TelemetryHistoryResponse(BaseModel):
    vehicle_id: int
    events: List[Any] # Raw JSON events

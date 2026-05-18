from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class TelemetryIngestRequest(BaseModel):
    speed_kmh: float = Field(..., ge=0.0, description="Current speed in km/h")
    fuel_level_percentage: float = Field(..., ge=0.0, le=100.0, description="Fuel level percentage (0-100)")
    battery_voltage: float = Field(..., ge=0.0, description="Battery voltage")
    ignition_state: bool = Field(..., description="Ignition state (True = ON, False = OFF)")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Time of reading")

class TelemetryResponse(TelemetryIngestRequest):
    id: UUID
    organization_id: int
    vehicle_id: UUID

    class Config:
        from_attributes = True

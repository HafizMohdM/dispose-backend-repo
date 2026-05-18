from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TelemetryIngestPayload(BaseModel):
    vehicle_id: int = Field(..., description="Target vehicle asset identifier")
    speed_kmh: float = Field(0.0, ge=0.0, le=300.0, description="Realtime vehicle speed in km/h")
    fuel_level_percentage: float = Field(100.0, ge=0.0, le=100.0, description="Fuel level percentage")
    battery_voltage: float = Field(12.0, ge=0.0, le=100.0, description="Battery voltage")
    ignition_state: bool = Field(False, description="Ignition status (on/off)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS Latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS Longitude coordinate")
    heading: Optional[float] = Field(0.0, ge=0.0, le=360.0)
    speed: Optional[float] = Field(0.0, ge=0.0)

class TelemetryResponse(BaseModel):
    id: str
    vehicle_id: int
    speed_kmh: float
    fuel_level_percentage: float
    battery_voltage: float
    ignition_state: bool
    timestamp: datetime

    class Config:
        from_attributes = True

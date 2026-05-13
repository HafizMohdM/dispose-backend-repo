from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class VehicleCreate(BaseModel):
    registration_number: str
    vehicle_type: str
    fuel_type: Optional[str] = "Diesel"
    capacity_kg: Optional[float] = 0.0

class VehicleHealthResponse(BaseModel):
    engine_status: str
    battery_health: int
    fuel_level: int
    tire_pressure: str
    updated_at: datetime

class VehicleResponse(BaseModel):
    id: int
    registration_number: str
    vehicle_type: str
    fuel_type: str
    capacity_kg: float
    status: str
    created_at: datetime
    health: Optional[VehicleHealthResponse] = None

    class Config:
        from_attributes = True

class VehicleAssignmentRequest(BaseModel):
    driver_id: int

class MaintenanceLogCreate(BaseModel):
    maintenance_type: str
    notes: Optional[str] = None
    next_due_date: Optional[datetime] = None
    cost: Optional[float] = 0.0

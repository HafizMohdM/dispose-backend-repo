from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.vehicle import VehicleStatus, MaintenanceStatus

class VehicleBase(BaseModel):
    registration_number: str = Field(..., description="Unique registration number of the vehicle")
    vehicle_type: str = Field(..., description="Type of the vehicle, e.g., Truck, Van, Loader")
    fuel_type: Optional[str] = Field(None, description="Fuel type, e.g., Diesel, EV, Petrol, CNG")
    capacity_kg: Optional[float] = Field(0.0, description="Load capacity in kilograms")
    status: Optional[VehicleStatus] = Field(VehicleStatus.INACTIVE, description="Current status of the vehicle")

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    fuel_type: Optional[str] = None
    capacity_kg: Optional[float] = None
    status: Optional[VehicleStatus] = None

class VehicleResponse(VehicleBase):
    id: UUID
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AssignDriverRequest(BaseModel):
    driver_id: UUID = Field(..., description="The UUID of the driver to assign")

class VehicleAssignmentResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    driver_id: UUID
    is_active: bool
    assigned_at: datetime
    unassigned_at: Optional[datetime]

    class Config:
        from_attributes = True

class VehicleMaintenanceCreate(BaseModel):
    description: str
    cost: Optional[float] = None
    scheduled_date: datetime

class VehicleMaintenanceResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    organization_id: int
    description: str
    cost: Optional[float]
    status: MaintenanceStatus
    scheduled_date: datetime
    completed_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FleetHealthResponse(BaseModel):
    total_vehicles: int
    active_vehicles: int
    in_maintenance: int
    inactive_vehicles: int
    critical_alerts: int

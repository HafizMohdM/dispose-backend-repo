from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.sustainability import MetricType

class ExecutiveSummaryResponse(BaseModel):
    active_vehicles: int
    active_trips: int
    total_waste_weight: float
    active_incidents: int

class SustainabilityMetricsResponse(BaseModel):
    total_waste_weight_kg: float
    co2_saved_kg: float
    clean_energy_kwh: float

class EcoGoalResponse(BaseModel):
    id: int
    title: str
    target_value: float
    current_value: float
    metric_type: MetricType
    is_completed: bool
    deadline: Optional[datetime]

    class Config:
        from_attributes = True

class EcoGoalsListResponse(BaseModel):
    goals: List[EcoGoalResponse]

class PerformanceIntelligenceResponse(BaseModel):
    success_rate_percentage: float
    completed_pickups: int
    total_pickups: int

class SystemHealthResponse(BaseModel):
    database_status: str
    microservices_online: int
    open_incident_bottlenecks: int

class CO2MetricsResponse(BaseModel):
    co2_saved_kg: float

class EnergyRecoveryResponse(BaseModel):
    clean_energy_kwh: float

class LiveNode(BaseModel):
    id: str
    latitude: float
    longitude: float
    node_type: str

class LiveNodesResponse(BaseModel):
    nodes: List[LiveNode]

class ConversionRateResponse(BaseModel):
    conversion_ratio: float
    completed_pickups: int
    blocked_pickups: int

class FulfillmentHealthResponse(BaseModel):
    health_score: float
    total_assignments: int
    completed_assignments: int

class GoalUpdate(BaseModel):
    current_value: float

class GoalProgressResponse(BaseModel):
    id: int
    title: str
    progress_percentage: float
    is_completed: bool
    remaining_value: float

class DashboardLiveKpisResponse(BaseModel):
    pickups_today: int
    completed_today: int
    revenue_today: float

class DashboardLiveFleetResponse(BaseModel):
    active_vehicles: int
    total_vehicles: int
    incidents_today: int

class MapCoordinate(BaseModel):
    latitude: float
    longitude: float

class DashboardLiveMapResponse(BaseModel):
    active_drivers: List[MapCoordinate]

class DashboardTelemetryResponse(BaseModel):
    total_telemetry_events: int
    avg_speed_kmh: float

class DashboardVehicleHealthResponse(BaseModel):
    total_vehicles: int
    in_maintenance: int
    critical_alerts: int

class DashboardNetworkHealthResponse(BaseModel):
    websocket_connections_active: int
    message_queue_status: str

class DashboardCapacityResponse(BaseModel):
    total_capacity_kg: float
    utilized_capacity_kg: float

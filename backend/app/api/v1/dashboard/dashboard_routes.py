from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.services.dashboard_service import DashboardService
from app.api.v1.dashboard.dashboard_schemas import (
    ExecutiveSummaryResponse,
    SustainabilityMetricsResponse,
    PerformanceIntelligenceResponse,
    EcoGoalsListResponse,
    SystemHealthResponse,
    CO2MetricsResponse,
    EnergyRecoveryResponse,
    LiveNodesResponse,
    ConversionRateResponse,
    FulfillmentHealthResponse,
    GoalUpdate,
    GoalProgressResponse,
    DashboardLiveKpisResponse,
    DashboardLiveFleetResponse,
    DashboardLiveMapResponse,
    DashboardTelemetryResponse,
    DashboardVehicleHealthResponse,
    DashboardNetworkHealthResponse,
    DashboardCapacityResponse
)
from typing import List

router = APIRouter()

def get_org_id(current_user) -> int:
    org_id = getattr(current_user, "current_org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required."
        )
    return org_id

@router.get("/executive-summary", response_model=ExecutiveSummaryResponse)
def get_executive_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("fleet.view"))
):
    service = DashboardService(db)
    return service.get_executive_summary(get_org_id(current_user))

@router.get("/sustainability", response_model=SustainabilityMetricsResponse)
def get_sustainability_metrics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_sustainability_metrics(get_org_id(current_user))

@router.get("/performance", response_model=PerformanceIntelligenceResponse)
def get_performance_intelligence(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_performance_intelligence(get_org_id(current_user))

@router.get("/goals", response_model=EcoGoalsListResponse)
def get_eco_goals(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_eco_goals(get_org_id(current_user))

@router.get("/system-health", response_model=SystemHealthResponse)
def get_system_health(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_system_health(get_org_id(current_user))

@router.get("/co2-metrics", response_model=CO2MetricsResponse)
def get_co2_metrics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_co2_metrics(get_org_id(current_user))

@router.get("/energy-recovery", response_model=EnergyRecoveryResponse)
def get_energy_recovery(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_energy_recovery(get_org_id(current_user))

@router.get("/environmental-goals", response_model=EcoGoalsListResponse)
def get_environmental_goals(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_eco_goals(get_org_id(current_user))

@router.get("/live-nodes", response_model=LiveNodesResponse)
def get_live_nodes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_live_nodes(get_org_id(current_user))

@router.get("/conversion-rate", response_model=ConversionRateResponse)
def get_conversion_rate(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_conversion_rate(get_org_id(current_user))

@router.get("/fulfillment-health", response_model=FulfillmentHealthResponse)
def get_fulfillment_health(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_fulfillment_health(get_org_id(current_user))

@router.patch("/goals/{id}", response_model=GoalProgressResponse)
def update_goal(
    id: int,
    request: GoalUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.manage"))
):
    service = DashboardService(db)
    return service.update_eco_goal(id, get_org_id(current_user), request)

@router.get("/goals/progress", response_model=List[GoalProgressResponse])
def get_goal_progress(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_goal_progress(get_org_id(current_user))

@router.get("/live-kpis", response_model=DashboardLiveKpisResponse)
def get_live_kpis(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_live_kpis(get_org_id(current_user))

@router.get("/live-fleet", response_model=DashboardLiveFleetResponse)
def get_live_fleet(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_live_fleet(get_org_id(current_user))

@router.get("/live-map", response_model=DashboardLiveMapResponse)
def get_live_map(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_live_map(get_org_id(current_user))

@router.get("/telemetry", response_model=DashboardTelemetryResponse)
def get_telemetry(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_telemetry(get_org_id(current_user))

@router.get("/vehicle-health", response_model=DashboardVehicleHealthResponse)
def get_vehicle_health(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_vehicle_health(get_org_id(current_user))

@router.get("/network-health", response_model=DashboardNetworkHealthResponse)
def get_network_health(
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(None)  # Network health doesn't need DB in this abstraction
    return service.get_network_health()

@router.get("/capacity", response_model=DashboardCapacityResponse)
def get_capacity(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("analytics.view"))
):
    service = DashboardService(db)
    return service.get_capacity(get_org_id(current_user))

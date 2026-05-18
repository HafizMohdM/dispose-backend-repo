from sqlalchemy.orm import Session
from app.repositories.dashboard_repo import DashboardRepository
from app.api.v1.dashboard.dashboard_schemas import (
    ExecutiveSummaryResponse,
    SustainabilityMetricsResponse,
    PerformanceIntelligenceResponse,
    EcoGoalsListResponse,
    SystemHealthResponse,
    CO2MetricsResponse,
    EnergyRecoveryResponse,
    LiveNode,
    LiveNodesResponse,
    ConversionRateResponse,
    FulfillmentHealthResponse,
    GoalUpdate,
    GoalProgressResponse,
    DashboardLiveKpisResponse,
    DashboardLiveFleetResponse,
    MapCoordinate,
    DashboardLiveMapResponse,
    DashboardTelemetryResponse,
    DashboardVehicleHealthResponse,
    DashboardNetworkHealthResponse,
    DashboardCapacityResponse
)
from fastapi import HTTPException

class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardRepository(db)

    def get_executive_summary(self, organization_id: int) -> ExecutiveSummaryResponse:
        return ExecutiveSummaryResponse(
            active_vehicles=self.repo.get_active_vehicles_count(organization_id),
            active_trips=self.repo.get_active_trips_count(organization_id),
            total_waste_weight=self.repo.get_total_waste_weight(organization_id),
            active_incidents=self.repo.get_active_incidents_count(organization_id)
        )

    def get_sustainability_metrics(self, organization_id: int) -> SustainabilityMetricsResponse:
        total_weight, co2_saved, clean_energy = self.repo.get_sustainability_kpis(organization_id)
        
        return SustainabilityMetricsResponse(
            total_waste_weight_kg=total_weight,
            co2_saved_kg=co2_saved,
            clean_energy_kwh=clean_energy
        )

    def get_performance_intelligence(self, organization_id: int) -> PerformanceIntelligenceResponse:
        completed = self.repo.get_completed_pickups_count(organization_id)
        total = self.repo.get_total_pickups_count(organization_id)
        success_rate = (completed / total * 100) if total > 0 else 0.0
        
        return PerformanceIntelligenceResponse(
            success_rate_percentage=success_rate,
            completed_pickups=completed,
            total_pickups=total
        )

    def get_eco_goals(self, organization_id: int) -> EcoGoalsListResponse:
        goals = self.repo.get_eco_goals(organization_id)
        return EcoGoalsListResponse(goals=goals)

    def get_system_health(self, organization_id: int) -> SystemHealthResponse:
        active_incidents = self.repo.get_active_incidents_count(organization_id)
        return SystemHealthResponse(
            database_status="CONNECTED",
            microservices_online=5,
            open_incident_bottlenecks=active_incidents
        )

    def get_co2_metrics(self, organization_id: int) -> CO2MetricsResponse:
        _, co2_saved_kg, _ = self.repo.get_sustainability_kpis(organization_id)
        return CO2MetricsResponse(co2_saved_kg=co2_saved_kg)

    def get_energy_recovery(self, organization_id: int) -> EnergyRecoveryResponse:
        _, _, clean_energy_kwh = self.repo.get_sustainability_kpis(organization_id)
        return EnergyRecoveryResponse(clean_energy_kwh=clean_energy_kwh)

    def get_live_nodes(self, organization_id: int) -> LiveNodesResponse:
        pickup_nodes = self.repo.get_live_pickup_nodes(organization_id)
        nodes = []
        for p in pickup_nodes:
            nodes.append(LiveNode(
                id=f"pickup_{p.id}",
                latitude=p.latitude,
                longitude=p.longitude,
                node_type="DROP_OFF_ZONE"
            ))
        return LiveNodesResponse(nodes=nodes)

    def get_conversion_rate(self, organization_id: int) -> ConversionRateResponse:
        completed = self.repo.get_completed_pickups_count(organization_id)
        blocked = self.repo.get_blocked_pickups_count(organization_id)
        total = completed + blocked
        ratio = (completed / total) if total > 0 else 0.0
        return ConversionRateResponse(
            conversion_ratio=ratio,
            completed_pickups=completed,
            blocked_pickups=blocked
        )

    def get_fulfillment_health(self, organization_id: int) -> FulfillmentHealthResponse:
        total_assignments, completed_assignments = self.repo.get_assignments_counts(organization_id)
        health_score = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0.0
        return FulfillmentHealthResponse(
            health_score=health_score,
            total_assignments=total_assignments,
            completed_assignments=completed_assignments
        )

    def update_eco_goal(self, goal_id: int, organization_id: int, request: GoalUpdate) -> GoalProgressResponse:
        goal = self.repo.get_eco_goal_by_id(goal_id, organization_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        self.repo.update_eco_goal_atomic(goal_id, organization_id, request.current_value)
        
        # Fetch updated goal state
        goal = self.repo.get_eco_goal_by_id(goal_id, organization_id)
        
        progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0.0
        remaining = max(0.0, float(goal.target_value - goal.current_value))
        
        return GoalProgressResponse(
            id=goal.id,
            title=goal.title,
            progress_percentage=min(progress, 100.0),
            is_completed=goal.is_completed,
            remaining_value=remaining
        )

    def get_goal_progress(self, organization_id: int) -> list[GoalProgressResponse]:
        goals = self.repo.get_eco_goals(organization_id)
        responses = []
        for goal in goals:
            progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0.0
            remaining = max(0.0, float(goal.target_value - goal.current_value))
            responses.append(GoalProgressResponse(
                id=goal.id,
                title=goal.title,
                progress_percentage=min(progress, 100.0),
                is_completed=goal.is_completed,
                remaining_value=remaining
            ))
        return responses

    def get_live_kpis(self, organization_id: int) -> DashboardLiveKpisResponse:
        pickups_today, completed_today = self.repo.get_todays_kpis(organization_id)
        revenue_today = completed_today * 150.0
        return DashboardLiveKpisResponse(
            pickups_today=pickups_today,
            completed_today=completed_today,
            revenue_today=revenue_today
        )

    def get_live_fleet(self, organization_id: int) -> DashboardLiveFleetResponse:
        total, in_maintenance, _ = self.repo.get_vehicle_fleet_health(organization_id)
        active = self.repo.get_active_vehicles_count(organization_id)
        incidents = self.repo.get_active_incidents_count(organization_id)
        return DashboardLiveFleetResponse(
            active_vehicles=active,
            total_vehicles=total,
            incidents_today=incidents
        )

    def get_live_map(self, organization_id: int) -> DashboardLiveMapResponse:
        locations = self.repo.get_live_drivers_locations(organization_id)
        coords = [MapCoordinate(latitude=loc.latitude, longitude=loc.longitude) for loc in locations]
        return DashboardLiveMapResponse(active_drivers=coords)

    def get_telemetry(self, organization_id: int) -> DashboardTelemetryResponse:
        return DashboardTelemetryResponse(
            total_telemetry_events=12054,
            avg_speed_kmh=42.5
        )

    def get_vehicle_health(self, organization_id: int) -> DashboardVehicleHealthResponse:
        total, in_maintenance, critical_alerts = self.repo.get_vehicle_fleet_health(organization_id)
        return DashboardVehicleHealthResponse(
            total_vehicles=total,
            in_maintenance=in_maintenance,
            critical_alerts=critical_alerts
        )

    def get_network_health(self) -> DashboardNetworkHealthResponse:
        return DashboardNetworkHealthResponse(
            websocket_connections_active=42,
            message_queue_status="HEALTHY"
        )

    def get_capacity(self, organization_id: int) -> DashboardCapacityResponse:
        total, utilized = self.repo.get_fleet_capacity(organization_id)
        return DashboardCapacityResponse(
            total_capacity_kg=total,
            utilized_capacity_kg=utilized
        )

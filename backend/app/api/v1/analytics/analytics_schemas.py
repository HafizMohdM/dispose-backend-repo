from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# --- LEGACY SCHEMAS ---
class DashboardResponse(BaseModel):
    total_pickups: int
    completed_pickups: int
    pending_pickups: int
    cancelled_pickups: int
    active_drivers: int
    inactive_drivers: int
    total_organizations: int
    monthly_revenue: Decimal
    active_subscriptions: int
    failed_payments: int

class PickupTrend(BaseModel):
    date: date
    count: int

class PickupAnalyticsResponse(BaseModel):
    pickup_trends: List[PickupTrend]
    status_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    completion_percentage: float
    total_weight: float

class DriverPerformance(BaseModel):
    driver_name: str
    completed_pickups: int
    total_weight: float
    avg_rating: float

class DriverAnalyticsResponse(BaseModel):
    active_drivers: int
    busy_drivers: int
    inactive_drivers: int
    top_performing_drivers: List[DriverPerformance]
    driver_utilization: float

class RevenueAnalyticsResponse(BaseModel):
    total_revenue: Decimal
    monthly_revenue: Decimal
    successful_payments: int
    failed_payments: int
    refund_amount: Decimal
    growth_percentage: float

class SubscriptionAnalyticsResponse(BaseModel):
    active_subscriptions: int
    cancelled_subscriptions: int
    upgrades: int
    downgrades: int
    plan_distribution: Dict[str, int]

class SecurityAnalyticsResponse(BaseModel):
    login_activity: List[Dict]
    failed_login_attempts: int
    suspicious_actions: int
    admin_activity: List[Dict]
    audit_statistics: Dict[str, int]

class VolumeTrendData(BaseModel):
    date: date
    total_pickups: int
    total_weight: float

class VolumeTrendResponse(BaseModel):
    trends: List[VolumeTrendData]

class VolumeDashboardMetricsResponse(BaseModel):
    total_active_pickups: int
    total_completed_this_month: int
    sla_breach_count: int

# --- MODERN CQRS SCHEMAS ---
class LiveKpisResponse(BaseModel):
    pickups_today: int
    completed_today: int
    waste_collected_kg: float
    revenue_today: float
    co2_saved_kg: float

class TrendPoint(BaseModel):
    date: str
    pickups: int
    revenue: float
    waste_kg: float

class SustainabilitySummary(BaseModel):
    co2_saved_total_kg: float
    waste_diverted_kg: float
    recycling_rate: float

class FleetOverview(BaseModel):
    online_drivers: int
    timestamp: datetime

class ExecutiveSummaryResponse(BaseModel):
    live_status: LiveKpisResponse
    trends: List[TrendPoint]
    sustainability: SustainabilitySummary
    fleet_overview: FleetOverview

class PerformanceTrendResponse(BaseModel):
    date: str
    revenue: float
    pickups: int
    efficiency_score: float

class ESGGoalResponse(BaseModel):
    title: str
    target: float
    current: float
    progress_pct: float
    unit: str
    status: str

class SustainabilityReportResponse(BaseModel):
    current_metrics: Dict[str, float]
    goals: List[ESGGoalResponse]

class LiveFleetResponse(BaseModel):
    active_vehicles: int
    total_vehicles: int
    idle_vehicles: int
    incidents_today: int

class SystemHealthResponse(BaseModel):
    api_status: str
    redis_status: str
    celery_workers_online: int
    last_aggregation_run: Optional[datetime] = None
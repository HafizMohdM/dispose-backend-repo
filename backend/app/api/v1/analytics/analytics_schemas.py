from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, date
from decimal import Decimal

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
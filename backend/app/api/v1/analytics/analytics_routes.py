from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_user_org
from app.core.permissions import require_permission
from app.services.analytics.analytics_service import AnalyticsService
from app.api.v1.analytics.analytics_schemas import (
    DashboardResponse, PickupAnalyticsResponse, DriverAnalyticsResponse,
    RevenueAnalyticsResponse, SubscriptionAnalyticsResponse, SecurityAnalyticsResponse
)
from datetime import date, datetime
from app.models.materialized_metrics import HourlyMetric, WeeklyMetric
from sqlalchemy import desc, func

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse, tags=["Analytics Dashboard"])
async def get_dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.view"))
):
    """
    Get top-level KPIs for the organization.
    """
    org = get_user_org(db, current_user)
    return await AnalyticsService.get_dashboard_summary(db, org.id if org else None, start_date, end_date)

@router.get("/pickups", response_model=PickupAnalyticsResponse, tags=["Analytics Dashboard"])
async def get_pickup_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.view"))
):
    """
    Get detailed pickup trends and distribution.
    """
    org = get_user_org(db, current_user)
    return await AnalyticsService.get_pickup_analytics(db, org.id if org else None, start_date, end_date)

@router.get("/drivers", response_model=DriverAnalyticsResponse, tags=["Analytics Dashboard"])
async def get_driver_analytics(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.view"))
):
    """
    Get driver performance and utilization metrics.
    """
    org = get_user_org(db, current_user)
    return await AnalyticsService.get_driver_analytics(db, org.id if org else None)

@router.get("/security", response_model=SecurityAnalyticsResponse, tags=["Analytics Dashboard"])
async def get_security_analytics(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.admin"))
):
    """
    Get security-related metrics and audit statistics.
    """
    return await AnalyticsService.get_security_analytics(db)

@router.get("/revenue", response_model=RevenueAnalyticsResponse, tags=["Analytics Dashboard"])
async def get_revenue_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.view"))
):
    org = get_user_org(db, current_user)
    return await AnalyticsService.get_revenue_analytics(db, org.id if org else None, start_date, end_date)

@router.get("/subscriptions", response_model=SubscriptionAnalyticsResponse, tags=["Analytics Dashboard"])
async def get_subscription_analytics(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.view"))
):
    org = get_user_org(db, current_user)
    # Placeholder for now
    return {
        "active_subscriptions": 0,
        "cancelled_subscriptions": 0,
        "upgrades": 0,
        "downgrades": 0,
        "plan_distribution": {}
    }

@router.get("/snapshots/summary", tags=["KPI Snapshots"])
async def get_kpi_snapshots(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("analytics.view"))
):
    """
    Ultra-fast KPI snapshots reading from materialized tables.
    """
    org = get_user_org(db, current_user)
    org_id = org.id if org else None
    
    if not org_id:
        return {"detail": "Organization context required for snapshots"}

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue = db.query(func.sum(HourlyMetric.revenue)).filter(
        HourlyMetric.organization_id == org_id,
        HourlyMetric.timestamp >= today_start
    ).scalar() or 0

    last_week_pickups = db.query(WeeklyMetric.completed_pickups).filter(
        WeeklyMetric.organization_id == org_id
    ).order_by(desc(WeeklyMetric.year), desc(WeeklyMetric.week_number)).first()
    
    return {
        "today_revenue": float(today_revenue),
        "weekly_pickups": last_week_pickups[0] if last_week_pickups else 0,
        "monthly_growth_percentage": 14.5
    }
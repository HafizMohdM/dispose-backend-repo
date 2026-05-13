from sqlalchemy.orm import Session
from app.repositories.analytics_repo import AnalyticsRepository
from app.api.v1.analytics.analytics_schemas import (
    DashboardResponse, PickupAnalyticsResponse, DriverAnalyticsResponse,
    RevenueAnalyticsResponse, SubscriptionAnalyticsResponse, SecurityAnalyticsResponse
)
from datetime import date, timedelta
from typing import Optional, List, Dict
from app.core.cache import cached
from app.utils.query_utils import PaginationParams

class AnalyticsService:
    @staticmethod
    @cached(ttl=300, prefix="analytics:dashboard")
    async def get_dashboard_summary(db: Session, org_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
        # Note: cached decorator needs to be async if it calls await func
        # and it returns dict which is JSON serializable
        data = AnalyticsRepository.get_dashboard_kpis(db, org_id, start_date, end_date)
        return data

    @staticmethod
    @cached(ttl=600, prefix="analytics:pickups")
    async def get_pickup_analytics(db: Session, org_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
        if not end_date: end_date = date.today()
        if not start_date: start_date = end_date - timedelta(days=30)
        
        trends = AnalyticsRepository.get_pickup_trends(db, org_id, start_date, end_date)
        statuses = AnalyticsRepository.get_status_distribution(db, org_id, start_date, end_date)
        categories = AnalyticsRepository.get_waste_type_distribution(db, org_id, start_date, end_date)
        
        # Calculate completion percentage
        status_dict = {str(s[0].value): s[1] for s in statuses}
        total = sum(status_dict.values())
        completed = status_dict.get("COMPLETED", 0)
        completion_rate = (completed / total * 100) if total > 0 else 0.0
        
        return {
            "pickup_trends": [{"date": t.date, "count": t.count} for t in trends],
            "status_distribution": status_dict,
            "category_distribution": {str(c[0].value): c[1] for c in categories},
            "completion_percentage": completion_rate,
            "total_weight": 0.0 # Placeholder
        }

    @staticmethod
    @cached(ttl=600, prefix="analytics:drivers")
    async def get_driver_analytics(db: Session, org_id: Optional[int] = None) -> Dict:
        top_drivers = AnalyticsRepository.get_top_drivers(db, org_id)
        
        return {
            "active_drivers": 0,
            "busy_drivers": 0,
            "inactive_drivers": 0,
            "top_performing_drivers": [
                {
                    "driver_name": d.name,
                    "completed_pickups": d.completed_count,
                    "total_weight": float(d.total_weight or 0),
                    "avg_rating": 4.5
                } for d in top_drivers
            ],
            "driver_utilization": 0.0
        }

    @staticmethod
    @cached(ttl=900, prefix="analytics:revenue")
    async def get_revenue_analytics(db: Session, org_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
        data = AnalyticsRepository.get_dashboard_kpis(db, org_id, start_date, end_date)
        return {
            "total_revenue": data["monthly_revenue"], # Placeholder for lifetime
            "monthly_revenue": data["monthly_revenue"],
            "successful_payments": data["completed_pickups"], # Needs proper mapping
            "failed_payments": data["failed_payments"],
            "refund_amount": 0.0,
            "growth_percentage": 0.0
        }

    @staticmethod
    async def get_security_analytics(db: Session) -> Dict:
        stats = AnalyticsRepository.get_security_stats(db)
        
        return {
            "login_activity": [],
            "failed_login_attempts": stats["failed_logins"],
            "suspicious_actions": stats["suspicious_actions"],
            "admin_activity": [],
            "audit_statistics": {str(a[0]): a[1] for a in stats["admin_actions"]}
        }


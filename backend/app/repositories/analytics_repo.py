from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc, extract, case, text
import sqlalchemy as sa
from typing import List, Optional, Dict, Any
from app.models.analytics import AnalyticsEvent, DailyMetric, PickupMetric, DriverMetric, RevenueMetric
from app.models.pickup import Pickup, PickupStatus, WasteType
from app.models.user import User
from app.models.organization import Organization
from app.models.payment import Payment, PaymentStatus
from app.models.invoice import Invoice
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.audit_log import AuditLog
from datetime import datetime, timedelta, date
from decimal import Decimal
from app.utils.query_utils import PaginationParams, paginate_query

class AnalyticsRepository:
    @staticmethod
    def get_dashboard_kpis(db: Session, org_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None):
        # Base filters
        pickup_filter = []
        if org_id:
            pickup_filter.append(Pickup.organization_id == org_id)
        if start_date:
            pickup_filter.append(Pickup.created_at >= start_date)
        if end_date:
            pickup_filter.append(Pickup.created_at <= end_date)

        # 1. Optimized Pickup Stats using single query
        pickup_stats = db.query(
            func.count(Pickup.id).label("total"),
            func.sum(case((Pickup.status == PickupStatus.COMPLETED, 1), else_=0)).label("completed"),
            func.sum(case((Pickup.status == PickupStatus.PENDING, 1), else_=0)).label("pending"),
            func.sum(case((Pickup.status == PickupStatus.CANCELLED, 1), else_=0)).label("cancelled")
        ).filter(*pickup_filter).first()

        # 2. Revenue (Current Month or Range)
        rev_filter = [Payment.status == PaymentStatus.SUCCESS]
        if org_id:
            rev_filter.append(Invoice.organization_id == org_id)
        
        if start_date:
            rev_filter.append(Payment.created_at >= start_date)
        else:
            rev_filter.append(Payment.created_at >= date.today().replace(day=1))
            
        if end_date:
            rev_filter.append(Payment.created_at <= end_date)

        monthly_revenue = db.query(func.sum(Payment.amount)).join(Invoice).filter(*rev_filter).scalar() or Decimal("0.00")

        # 3. Failed Payments
        failed_filter = [Payment.status == PaymentStatus.FAILED]
        if org_id:
            failed_filter.append(Invoice.organization_id == org_id)
        failed_payments = db.query(func.count(Payment.id)).join(Invoice).filter(*failed_filter).scalar() or 0

        # 4. Active Subscriptions
        active_subs = db.query(func.count(Subscription.id)).filter(
            Subscription.organization_id == org_id if org_id else True,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).scalar() or 0

        return {
            "total_pickups": pickup_stats.total or 0,
            "completed_pickups": pickup_stats.completed or 0,
            "pending_pickups": pickup_stats.pending or 0,
            "cancelled_pickups": pickup_stats.cancelled or 0,
            "monthly_revenue": monthly_revenue,
            "active_subscriptions": active_subs,
            "failed_payments": failed_payments,
            "active_drivers": 0, 
            "inactive_drivers": 0,
            "total_organizations": db.query(func.count(Organization.id)).scalar() if not org_id else 1
        }

    @staticmethod
    def get_pickup_trends(db: Session, org_id: Optional[int], start_date: date, end_date: date, pagination: Optional[PaginationParams] = None):
        query = db.query(
            func.date(Pickup.created_at).label("date"),
            func.count(Pickup.id).label("count")
        ).filter(
            Pickup.organization_id == org_id if org_id else True,
            func.date(Pickup.created_at) >= start_date,
            func.date(Pickup.created_at) <= end_date
        ).group_by(func.date(Pickup.created_at)).order_by(desc("date"))
        
        if pagination:
            return paginate_query(query, pagination)
        return query.all()

    @staticmethod
    def get_status_distribution(db: Session, org_id: Optional[int], start_date: Optional[date] = None, end_date: Optional[date] = None):
        filters = []
        if org_id: filters.append(Pickup.organization_id == org_id)
        if start_date: filters.append(func.date(Pickup.created_at) >= start_date)
        if end_date: filters.append(func.date(Pickup.created_at) <= end_date)
        
        return db.query(
            Pickup.status,
            func.count(Pickup.id)
        ).filter(*filters).group_by(Pickup.status).all()

    @staticmethod
    def get_waste_type_distribution(db: Session, org_id: Optional[int], start_date: Optional[date] = None, end_date: Optional[date] = None):
        filters = []
        if org_id: filters.append(Pickup.organization_id == org_id)
        if start_date: filters.append(func.date(Pickup.created_at) >= start_date)
        if end_date: filters.append(func.date(Pickup.created_at) <= end_date)
        
        return db.query(
            Pickup.waste_type,
            func.count(Pickup.id)
        ).filter(*filters).group_by(Pickup.waste_type).all()

    @staticmethod
    def get_top_drivers(db: Session, org_id: Optional[int], limit: int = 5):
        from app.models.pickup_assignment import PickupAssignment
        return db.query(
            User.id,
            User.mobile.label("name"),
            func.count(Pickup.id).label("completed_count"),
            func.sum(Pickup.waste_weight).label("total_weight")
        ).join(PickupAssignment, PickupAssignment.driver_id == User.id)\
         .join(Pickup, Pickup.id == PickupAssignment.pickup_id)\
         .filter(
             Pickup.status == PickupStatus.COMPLETED,
             Pickup.organization_id == org_id if org_id else True
         ).group_by(User.id).order_by(desc("completed_count")).limit(limit).all()

    @staticmethod
    def get_security_stats(db: Session, limit: int = 100):
        # Optimized with direct counts
        return {
            "failed_logins": db.query(func.count(AuditLog.id)).filter(AuditLog.event_type == "LOGIN_FAILED").scalar() or 0,
            "suspicious_actions": db.query(func.count(AuditLog.id)).filter(AuditLog.event_type == "SUSPICIOUS_ACTIVITY").scalar() or 0,
            "admin_actions": db.query(AuditLog.event_type, func.count(AuditLog.id)).group_by(AuditLog.event_type).all()
        }

    @staticmethod
    def get_volume_trends(db: Session, org_id: int, days: int):
        from sqlalchemy import cast, Date
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(
            func.date_trunc('day', Pickup.created_at).label('date'),
            func.count(Pickup.id).label('total_pickups'),
            func.sum(Pickup.waste_weight).label('total_weight')
        ).filter(
            Pickup.organization_id == org_id,
            Pickup.created_at >= start_date
        ).group_by(
            func.date_trunc('day', Pickup.created_at)
        ).order_by(
            func.date_trunc('day', Pickup.created_at).asc()
        )
        return query.all()

    @staticmethod
    def get_dashboard_metrics(db: Session, org_id: int):
        from sqlalchemy import case
        from app.models.pickup_exception import PickupException

        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        sla_breaches = db.query(func.count(PickupException.id)).join(
            Pickup, Pickup.id == PickupException.pickup_id
        ).filter(
            Pickup.organization_id == org_id
        ).scalar() or 0

        pickup_stats = db.query(
            func.sum(case((Pickup.status.in_([PickupStatus.PENDING, PickupStatus.ASSIGNED]), 1), else_=0)).label("active"),
            func.sum(case((and_(Pickup.status == PickupStatus.COMPLETED, Pickup.created_at >= start_of_month), 1), else_=0)).label("completed_month")
        ).filter(
            Pickup.organization_id == org_id
        ).first()

        return {
            "total_active_pickups": pickup_stats.active or 0,
            "total_completed_this_month": pickup_stats.completed_month or 0,
            "sla_breach_count": sla_breaches
        }
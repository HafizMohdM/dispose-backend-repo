from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.analytics import AnalyticsEvent, DailyMetric, EventType, PickupMetric
from app.models.sustainability import SustainabilityMetric
from sqlalchemy import func, and_
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.analytics.aggregate_daily_metrics")
def aggregate_daily_metrics():
    """
    Periodic task to materialize raw events into the daily_metrics table.
    Runs nightly or every few hours.
    """
    db = SessionLocal()
    try:
        yesterday = date.today() - timedelta(days=1)
        
        # 1. Get unique organizations that had activity
        org_ids = [r[0] for r in db.query(AnalyticsEvent.organization_id).filter(
            func.date(AnalyticsEvent.created_at) == yesterday
        ).distinct().all()]

        for org_id in org_ids:
            if not org_id: continue
            
            # Aggregate pickups
            total_pickups = db.query(AnalyticsEvent).filter(
                and_(
                    AnalyticsEvent.organization_id == org_id,
                    AnalyticsEvent.event_type == EventType.PICKUP_CREATED,
                    func.date(AnalyticsEvent.created_at) == yesterday
                )
            ).count()

            completed_pickups = db.query(AnalyticsEvent).filter(
                and_(
                    AnalyticsEvent.organization_id == org_id,
                    AnalyticsEvent.event_type == EventType.PICKUP_COMPLETED,
                    func.date(AnalyticsEvent.created_at) == yesterday
                )
            ).count()

            # Aggregate revenue
            revenue_events = db.query(AnalyticsEvent).filter(
                and_(
                    AnalyticsEvent.organization_id == org_id,
                    AnalyticsEvent.event_type == EventType.PAYMENT_SUCCESS,
                    func.date(AnalyticsEvent.created_at) == yesterday
                )
            ).all()
            total_rev = sum([float(e.event_metadata.get("amount", 0)) for e in revenue_events])

            # Upsert into DailyMetric
            metric = db.query(DailyMetric).filter(
                and_(DailyMetric.organization_id == org_id, DailyMetric.date == yesterday)
            ).first()
            
            if not metric:
                metric = DailyMetric(organization_id=org_id, date=yesterday)
                db.add(metric)
            
            metric.total_pickups = total_pickups
            metric.completed_pickups = completed_pickups
            metric.total_revenue = total_rev
            
        db.commit()
        logger.info(f"Successfully aggregated daily metrics for {len(org_ids)} organizations.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error aggregating daily metrics: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.tasks.analytics.calculate_sustainability_impact")
def calculate_sustainability_impact():
    """
    Nightly task to calculate ESG metrics from completed pickups.
    """
    db = SessionLocal()
    try:
        # Implementation similar to aggregate_daily_metrics but for sustainability
        pass 
    finally:
        db.close()

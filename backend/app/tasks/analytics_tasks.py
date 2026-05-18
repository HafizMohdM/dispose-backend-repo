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
    Nightly task to calculate ESG metrics from completed pickups using pure DB aggregations.
    """
    from app.models.pickup import Pickup, PickupStatus
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    try:
        yesterday = date.today() - timedelta(days=1)
        
        # Pure DB Computation Enforcements
        # Group by organization, calculate sum of waste_weight, and compute derived metrics natively
        results = db.query(
            Pickup.organization_id,
            func.coalesce(func.sum(Pickup.waste_weight), 0.0).label("waste_diverted"),
            (func.coalesce(func.sum(Pickup.waste_weight), 0.0) * 2.5).label("co2_saved"),
            (func.coalesce(func.sum(Pickup.waste_weight), 0.0) * 1.2).label("energy_saved")
        ).filter(
            func.date(Pickup.updated_at) == yesterday,
            Pickup.status == PickupStatus.COMPLETED
        ).group_by(
            Pickup.organization_id
        ).all()
        
        for org_id, waste_diverted, co2_saved, energy_saved in results:
            if not org_id: continue
            
            metric = db.query(SustainabilityMetric).filter(
                and_(SustainabilityMetric.organization_id == org_id, SustainabilityMetric.date == yesterday)
            ).first()
            
            if not metric:
                metric = SustainabilityMetric(organization_id=org_id, date=yesterday)
                db.add(metric)
                
            metric.waste_diverted_kg = float(waste_diverted)
            metric.co2_saved_kg = float(co2_saved)
            metric.energy_saved_kwh = float(energy_saved)
            
        db.commit()
        logger.info(f"Successfully calculated sustainability impact for {len(results)} organizations.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating sustainability impact: {str(e)}")
    finally:
        db.close()

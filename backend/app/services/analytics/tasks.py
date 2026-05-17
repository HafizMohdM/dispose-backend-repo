from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.analytics_repo import AnalyticsRepository
from app.models.analytics import DailyMetric
from app.models.materialized_metrics import HourlyMetric, WeeklyMetric, MonthlyMetric
from app.models.organization import Organization
from datetime import datetime, timedelta, date
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def aggregate_hourly_metrics():
    """
    Runs every hour to aggregate data from the previous hour.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        start_time = (now - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        orgs = db.query(Organization.id).all()
        for org_row in orgs:
            org_id = org_row[0]
            data = AnalyticsRepository.get_dashboard_kpis(db, org_id, start_time.date(), end_time.date())
            
            # Check if metric already exists
            metric = db.query(HourlyMetric).filter(
                HourlyMetric.organization_id == org_id,
                HourlyMetric.timestamp == start_time
            ).first()
            
            if not metric:
                metric = HourlyMetric(organization_id=org_id, timestamp=start_time)
                db.add(metric)
            
            metric.total_pickups = data["total_pickups"]
            metric.completed_pickups = data["completed_pickups"]
            metric.revenue = data["monthly_revenue"]
            
        db.commit()
        logger.info(f"Successfully aggregated hourly metrics for {start_time}")
    except Exception as e:
        logger.error(f"Error in hourly aggregation: {e}")
        db.rollback()
    finally:
        db.close()

@celery_app.task
def aggregate_daily_metrics(target_date_str: str = None):
    """
    Runs every midnight to reconcile the previous day. Can be manually triggered for a specific date.
    """
    db = SessionLocal()
    try:
        from app.models.pickup import Pickup, PickupStatus
        from sqlalchemy import func
        
        if target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            target_date = date.today() - timedelta(days=1)
            
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        orgs = db.query(Organization.id).all()
        for org_row in orgs:
            org_id = org_row[0]
            
            total_pickups = db.query(Pickup).filter(
                Pickup.organization_id == org_id,
                Pickup.created_at >= start_dt,
                Pickup.created_at <= end_dt
            ).count()

            completed_pickups = db.query(Pickup).filter(
                Pickup.organization_id == org_id,
                Pickup.status == PickupStatus.COMPLETED,
                Pickup.updated_at >= start_dt,
                Pickup.updated_at <= end_dt
            ).count()
            
            weight_query = db.query(func.sum(Pickup.actual_weight)).filter(
                Pickup.organization_id == org_id,
                Pickup.status == PickupStatus.COMPLETED,
                Pickup.updated_at >= start_dt,
                Pickup.updated_at <= end_dt
            ).scalar()
            waste_collected = float(weight_query) if weight_query else 0.0
            
            # Upsert into DailyMetric
            metric = db.query(DailyMetric).filter(
                DailyMetric.organization_id == org_id,
                DailyMetric.date == target_date
            ).first()
            
            if not metric:
                metric = DailyMetric(organization_id=org_id, date=target_date)
                db.add(metric)
            
            metric.total_pickups = total_pickups
            metric.completed_pickups = completed_pickups
            metric.total_waste_kg = waste_collected
            metric.total_co2_saved_kg = waste_collected * 0.51
            metric.total_revenue = 0.0 # Can be wired to Invoice table later
            
        db.commit()
        logger.info(f"Successfully aggregated daily metrics for {target_date}")
        return {"status": "success", "date": str(target_date), "orgs_processed": len(orgs)}
    except Exception as e:
        logger.error(f"Error in daily aggregation: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task
def aggregate_weekly_metrics():
    """
    Runs every Monday at midnight.
    """
    db = SessionLocal()
    try:
        today = date.today()
        # Get start of last week
        last_week_start = today - timedelta(days=today.weekday() + 7)
        year, week_num, _ = last_week_start.isocalendar()
        
        orgs = db.query(Organization.id).all()
        for org_row in orgs:
            org_id = org_row[0]
            # Get data for the whole week
            data = AnalyticsRepository.get_dashboard_kpis(db, org_id, last_week_start, last_week_start + timedelta(days=6))
            
            metric = db.query(WeeklyMetric).filter(
                WeeklyMetric.organization_id == org_id,
                WeeklyMetric.year == year,
                WeeklyMetric.week_number == week_num
            ).first()
            
            if not metric:
                metric = WeeklyMetric(organization_id=org_id, year=year, week_number=week_num)
                db.add(metric)
            
            metric.total_pickups = data["total_pickups"]
            metric.completed_pickups = data["completed_pickups"]
            metric.revenue = data["monthly_revenue"]
            
        db.commit()
        logger.info(f"Successfully aggregated weekly metrics for Week {week_num}, {year}")
    except Exception as e:
        logger.error(f"Error in weekly aggregation: {e}")
        db.rollback()
    finally:
        db.close()


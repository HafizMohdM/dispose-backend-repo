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
def aggregate_daily_metrics():
    """
    Runs every midnight to reconcile the previous day.
    """
    db = SessionLocal()
    try:
        yesterday = date.today() - timedelta(days=1)
        orgs = db.query(Organization.id).all()
        for org_row in orgs:
            org_id = org_row[0]
            data = AnalyticsRepository.get_dashboard_kpis(db, org_id, yesterday, yesterday)
            
            metric = db.query(DailyMetric).filter(
                DailyMetric.organization_id == org_id,
                DailyMetric.date == yesterday
            ).first()
            
            if not metric:
                metric = DailyMetric(organization_id=org_id, date=yesterday)
                db.add(metric)
            
            metric.total_pickups = data["total_pickups"]
            metric.completed_pickups = data["completed_pickups"]
            metric.total_revenue = data["monthly_revenue"]
            
        db.commit()
        logger.info(f"Successfully aggregated daily metrics for {yesterday}")
    except Exception as e:
        logger.error(f"Error in daily aggregation: {e}")
        db.rollback()
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


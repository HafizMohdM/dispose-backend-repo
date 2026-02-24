from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_organization
from app.core.permissions import require_permission

from app.services.driver_analytics_service import DriverAnalyticsService

router = APIRouter()


@router.get("/top-performing")
def get_top_performing_drivers(
    db: Session = Depends(get_db),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = DriverAnalyticsService(db)

    return service.get_top_performing_drivers(org.id)


@router.get("/utilization")
def get_driver_utilization(
    db: Session = Depends(get_db),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = DriverAnalyticsService(db)

    return service.get_driver_utilization(org.id)


@router.get("/performance/{driver_id}")
def get_driver_performance(
    driver_id: UUID,
    db: Session = Depends(get_db),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = DriverAnalyticsService(db)

    return service.get_driver_performance(
        org.id,
        driver_id,
    )
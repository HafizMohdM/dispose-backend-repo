from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_organization
from app.core.permissions import require_permission

from app.services.analytics_service import AnalyticsService

from app.api.v1.analytics.analytics_schemas import (
    OrganizationDashboardResponse,
    DriverAnalyticsResponse,
    PickupAnalyticsResponse,
    NotificationAnalyticsResponse,
    SubscriptionAnalyticsResponse,
    UserActivityAnalyticsResponse,
    SummaryDashboardResponse,
    TimeFilteredDashboardResponse,
)

router = APIRouter()




@router.get(
    "/summary",
    response_model=SummaryDashboardResponse,
)
def get_summary_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    try:

        result = service.get_summary_dashboard(
            organization_id=organization.id,
            requested_by=current_user.id,
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )



@router.get(
    "/organization",
    response_model=OrganizationDashboardResponse,
)
def get_organization_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_organization_dashboard(
        organization_id=organization.id,
        requested_by=current_user.id,
    )




@router.get(
    "/drivers",
    response_model=DriverAnalyticsResponse,
)
def get_driver_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_driver_dashboard(
        organization_id=organization.id,
        requested_by=current_user.id,
    )




@router.get(
    "/pickups",
    response_model=PickupAnalyticsResponse,
)
def get_pickup_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_pickup_dashboard(
        organization_id=organization.id,
        requested_by=current_user.id,
    )




@router.get(
    "/notifications",
    response_model=NotificationAnalyticsResponse,
)
def get_notification_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_notification_dashboard(
        organization_id=organization.id,
        requested_by=current_user.id,
    )




@router.get(
    "/subscriptions",
    response_model=SubscriptionAnalyticsResponse,
)
def get_subscription_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_subscription_dashboard(
        organization_id=organization.id,
        requested_by=current_user.id,
    )




@router.get(
    "/activity",
    response_model=UserActivityAnalyticsResponse,
)
def get_user_activity_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_user_activity_dashboard(
        organization_id=organization.id,
        requested_by=current_user.id,
    )




@router.get(
    "/time-filtered",
    response_model=TimeFilteredDashboardResponse,
)
def get_time_filtered_dashboard(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("analytics:view")),
):

    service = AnalyticsService(db)

    return service.get_time_filtered_summary(
        organization_id=organization.id,
        days=days,
        requested_by=current_user.id,
    )
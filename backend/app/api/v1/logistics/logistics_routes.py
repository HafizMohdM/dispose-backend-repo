from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.repositories.logistics_repo import LogisticsRepository
from app.services.route_optimization_service import RouteOptimizationService
from app.api.v1.logistics.logistics_schemas import (
    PickupExceptionResponse,
    ActivityTimelineResponse,
    NotificationEventResponse,
    LogisticsRouteOptimizeRequest,
    LogisticsRoutePlanResponse
)

router = APIRouter()

def get_org_id(current_user) -> int:
    org_id = getattr(current_user, "current_org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required."
        )
    return org_id

@router.get("/exceptions", response_model=List[PickupExceptionResponse])
def get_pickup_exceptions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("logistics.view"))
):
    """
    Hardened Pickup Exception Framework.
    Fetches all unresolved and recently resolved pickup exceptions.
    """
    org_id = get_org_id(current_user)
    exceptions = LogisticsRepository.get_pickup_exceptions(db, org_id)
    return exceptions

@router.get("/timeline", response_model=List[ActivityTimelineResponse])
def get_activity_timeline(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("logistics.view"))
):
    """
    Sequential Activity Timeline ledger.
    Zero N+1 regressions.
    """
    org_id = get_org_id(current_user)
    timeline = LogisticsRepository.get_activity_timeline(db, org_id)
    return timeline

@router.get("/notifications", response_model=List[NotificationEventResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Multi-tenant Notification Event router.
    Filters implicitly by organization boundary.
    """
    org_id = get_org_id(current_user)
    notifications = LogisticsRepository.get_notifications(db, org_id)
    return notifications

@router.post("/routes/optimize", response_model=LogisticsRoutePlanResponse)
async def optimize_route(
    request: LogisticsRouteOptimizeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("logistics.manage"))
):
    """
    Vehicle routing optimizer interface backed by Google OR-Tools.
    Parses geolocations into optimized multi-stop sequence polylines.
    """
    org_id = get_org_id(current_user)
    try:
        from app.api.v1.routes.route_schemas import RouteOptimizeRequest
        service_req = RouteOptimizeRequest(
            pickup_ids=request.pickup_ids,
            vehicle_id=request.vehicle_id,
            depot_latitude=request.depot_latitude,
            depot_longitude=request.depot_longitude
        )
        route_plan = await RouteOptimizationService.generate_optimized_route(db, org_id, service_req)
        return route_plan
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/routes", response_model=List[LogisticsRoutePlanResponse])
def get_route_plans(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _: bool = Depends(require_permission("logistics.view"))
):
    org_id = get_org_id(current_user)
    routes = LogisticsRepository.get_route_plans(db, org_id)
    return routes

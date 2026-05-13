from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.routes.route_schemas import RouteOptimizeRequest, OptimizedRouteResponse, RouteAssignRequest
from app.services.route_optimization_service import RouteOptimizationService
from app.repositories.route_optimization_repo import RouteOptimizationRepository
from app.core.dependencies import get_user_org
from typing import List, Optional

router = APIRouter()

@router.post("/optimize", response_model=OptimizedRouteResponse)
async def optimize_route(
    request: RouteOptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Calculates the most efficient sequence for a list of pickups.
    """
    org = get_user_org(db, current_user)
    route = await RouteOptimizationService.generate_optimized_route(
        db=db,
        org_id=org.id,
        vehicle_id=request.vehicle_id,
        pickup_ids=request.pickup_ids
    )
    return route

@router.get("/", response_model=List[OptimizedRouteResponse])
async def list_routes(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Lists all optimized routes for the organization.
    """
    org = get_user_org(db, current_user)
    return RouteOptimizationRepository.get_org_routes(db, org.id, status)

@router.get("/{id}", response_model=OptimizedRouteResponse)
async def get_route(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """
    Returns details for a specific optimized route and its waypoints.
    """
    route = RouteOptimizationRepository.get_route_by_id(db, id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route

@router.post("/{id}/assign")
async def assign_route(
    id: int,
    request: RouteAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """
    Assigns an optimized route to a driver.
    """
    route = await RouteOptimizationService.assign_route_to_driver(db, id, request.driver_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"status": "assigned"}

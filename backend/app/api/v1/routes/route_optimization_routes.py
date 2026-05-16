from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.dependencies import get_user_org
from app.models.user import User

from app.api.v1.routes.route_schemas import (
    RouteOptimizeRequest, 
    OptimizedRouteResponse, 
    RouteAssignRequest
)
from app.services.route_optimization_service import RouteOptimizationService
from app.repositories.route_optimization_repo import RouteOptimizationRepository

router = APIRouter()

@router.post("/optimize", response_model=OptimizedRouteResponse, status_code=status.HTTP_201_CREATED)
async def optimize_route(
    request: RouteOptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """Create an optimized route using TSP (OR-Tools)"""
    org = get_user_org(db, current_user)
    
    route = await RouteOptimizationService.generate_optimized_route(
        db=db,
        org_id=org.id,
        request=request
    )
    return route


@router.get("/", response_model=List[OptimizedRouteResponse])
async def list_routes(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """List all optimized routes for the organization"""
    org = get_user_org(db, current_user)
    return RouteOptimizationRepository.get_org_routes(db, org.id, status)


@router.get("/active", response_model=List[OptimizedRouteResponse])
async def get_active_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """List all currently active optimized routes (ACTIVE, DISPATCHED, IN_PROGRESS)"""
    org = get_user_org(db, current_user)
    return RouteOptimizationService.get_active_routes(db, org.id)


@router.get("/{route_id}", response_model=OptimizedRouteResponse)
async def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.view"))
):
    """Get details of a specific optimized route"""
    route = RouteOptimizationRepository.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Optional: Check organization ownership
    org = get_user_org(db, current_user)
    if route.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return route


@router.post("/{route_id}/assign", response_model=dict)
async def assign_route(
    route_id: int,
    request: RouteAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fleet.manage"))
):
    """Assign optimized route to a driver"""
    route = await RouteOptimizationService.assign_route_to_driver(
        db=db, 
        route_id=route_id, 
        driver_id=request.driver_id
    )
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return {"status": "success", "message": "Route assigned successfully", "route_id": route_id}
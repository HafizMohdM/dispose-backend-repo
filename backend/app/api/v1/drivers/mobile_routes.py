from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.routes.route_schemas import OptimizedRouteResponse
from app.repositories.route_optimization_repo import RouteOptimizationRepository
from app.models.route_optimization import OptimizedRoute, RouteWaypoint
from datetime import datetime
from typing import List

router = APIRouter()

@router.get("/active-route", response_model=OptimizedRouteResponse)
async def get_my_active_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("driver.view"))
):
    """
    Returns the optimized route currently assigned to the logged-in driver.
    """
    route = db.query(OptimizedRoute).filter(
        OptimizedRoute.driver_id == current_user.id,
        OptimizedRoute.status.in_(["assigned", "active"])
    ).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="No active route assigned")
    return route

@router.post("/waypoints/{id}/check-in")
async def waypoint_check_in(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("driver.manage"))
):
    """
    Marks the driver as arrived at a specific waypoint.
    """
    waypoint = db.query(RouteWaypoint).filter(RouteWaypoint.id == id).first()
    if not waypoint:
        raise HTTPException(status_code=404, detail="Waypoint not found")
    
    waypoint.arrival_time = datetime.utcnow()
    # Auto-start the route if this is the first waypoint
    if waypoint.stop_number == 1:
        waypoint.optimized_route.status = "active"
        waypoint.optimized_route.start_time = datetime.utcnow()
        
    db.commit()
    return {"status": "checked_in", "timestamp": waypoint.arrival_time}

@router.post("/waypoints/{id}/check-out")
async def waypoint_check_out(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("driver.manage"))
):
    """
    Marks the completion of a task at a waypoint (e.g., pickup finished).
    """
    waypoint = db.query(RouteWaypoint).filter(RouteWaypoint.id == id).first()
    if not waypoint:
        raise HTTPException(status_code=404, detail="Waypoint not found")
    
    waypoint.departure_time = datetime.utcnow()
    waypoint.is_completed = True
    
    # Check if this was the last waypoint
    total_waypoints = len(waypoint.optimized_route.waypoints)
    if waypoint.stop_number == total_waypoints:
        waypoint.optimized_route.status = "completed"
        waypoint.optimized_route.end_time = datetime.utcnow()
        
    db.commit()
    return {"status": "completed", "timestamp": waypoint.departure_time}

@router.get("/route-history", response_model=List[OptimizedRouteResponse])
async def get_my_route_history(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("driver.view"))
):
    """
    Returns the driver's recently completed routes.
    """
    routes = db.query(OptimizedRoute).filter(
        OptimizedRoute.driver_id == current_user.id,
        OptimizedRoute.status == "completed"
    ).order_by(OptimizedRoute.end_time.desc()).limit(limit).all()
    
    return routes

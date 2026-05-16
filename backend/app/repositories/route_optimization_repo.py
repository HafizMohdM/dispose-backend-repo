from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from app.models.route_optimization import OptimizedRoute, RouteWaypoint


class RouteOptimizationRepository:

    @staticmethod
    def create_route(db: Session, route: OptimizedRoute) -> OptimizedRoute:
        """Create a new optimized route"""
        db.add(route)
        db.flush()          # Get the ID without committing full transaction
        return route

    @staticmethod
    def get_route_by_id(db: Session, route_id: int) -> Optional[OptimizedRoute]:
        """Get route with all waypoints (eager loading)"""
        return db.query(OptimizedRoute).options(
            joinedload(OptimizedRoute.waypoints)
        ).filter(OptimizedRoute.id == route_id).first()

    @staticmethod
    def get_org_routes(
        db: Session, 
        org_id: int, 
        status: Optional[str] = None
    ) -> List[OptimizedRoute]:
        """Get all routes for an organization"""
        query = db.query(OptimizedRoute).options(
            joinedload(OptimizedRoute.waypoints)
        ).filter(OptimizedRoute.organization_id == org_id)
        
        if status:
            query = query.filter(OptimizedRoute.status == status)
        
        return query.order_by(OptimizedRoute.created_at.desc()).all()

    @staticmethod
    def add_waypoint(db: Session, waypoint: RouteWaypoint) -> RouteWaypoint:
        """Add a waypoint to a route"""
        db.add(waypoint)
        db.flush()
        return waypoint

    @staticmethod
    def get_active_routes(db: Session, org_id: int) -> List[OptimizedRoute]:
        """Get all active/dispatched/in_progress routes for an organization"""
        active_statuses = ["active", "dispatched", "in_progress", "ACTIVE", "DISPATCHED", "IN_PROGRESS"]
        return db.query(OptimizedRoute).options(
            joinedload(OptimizedRoute.waypoints)
        ).filter(
            OptimizedRoute.organization_id == org_id,
            OptimizedRoute.status.in_(active_statuses)
        ).order_by(OptimizedRoute.created_at.desc()).all()

    @staticmethod
    def update_waypoint_status(
        db: Session, 
        waypoint_id: int, 
        is_completed: bool
    ) -> Optional[RouteWaypoint]:
        """Update waypoint completion status"""
        waypoint = db.query(RouteWaypoint).filter(
            RouteWaypoint.id == waypoint_id
        ).first()
        
        if waypoint:
            waypoint.is_completed = is_completed
            if is_completed and not waypoint.arrival_time:
                waypoint.arrival_time = datetime.utcnow()
            db.flush()
        
        return waypoint
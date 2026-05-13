from sqlalchemy.orm import Session
from app.models.route_optimization import OptimizedRoute, RouteWaypoint
from typing import List, Optional
from datetime import datetime

class RouteOptimizationRepository:
    
    @staticmethod
    def create_route(db: Session, route: OptimizedRoute) -> OptimizedRoute:
        db.add(route)
        return route

    @staticmethod
    def get_route_by_id(db: Session, route_id: int) -> Optional[OptimizedRoute]:
        return db.query(OptimizedRoute).filter(OptimizedRoute.id == route_id).first()

    @staticmethod
    def get_org_routes(db: Session, org_id: int, status: Optional[str] = None) -> List[OptimizedRoute]:
        query = db.query(OptimizedRoute).filter(OptimizedRoute.organization_id == org_id)
        if status:
            query = query.filter(OptimizedRoute.status == status)
        return query.all()

    @staticmethod
    def add_waypoint(db: Session, waypoint: RouteWaypoint) -> RouteWaypoint:
        db.add(waypoint)
        return waypoint

    @staticmethod
    def update_waypoint_status(db: Session, waypoint_id: int, is_completed: bool):
        waypoint = db.query(RouteWaypoint).filter(RouteWaypoint.id == waypoint_id).first()
        if waypoint:
            waypoint.is_completed = is_completed
            if is_completed:
                waypoint.arrival_time = datetime.utcnow()
        return waypoint

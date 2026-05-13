from sqlalchemy.orm import Session
from app.repositories.route_optimization_repo import RouteOptimizationRepository
from app.models.route_optimization import OptimizedRoute, RouteWaypoint
from app.models.pickup import Pickup
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RouteOptimizationService:
    
    @staticmethod
    async def generate_optimized_route(db: Session, org_id: int, vehicle_id: int, pickup_ids: List[int]) -> OptimizedRoute:
        """
        Logic to sequence pickups efficiently. 
        In a production environment, this would call OR-Tools or a Routing API (Google/Mapbox).
        """
        # 1. Fetch Pickup Locations
        pickups = db.query(Pickup).filter(Pickup.id.in_(pickup_ids)).all()
        
        # 2. Basic Greedy Sequence (Placeholder for advanced TSP logic)
        # We sequence them by their creation/id for now
        sorted_pickups = sorted(pickups, key=lambda p: p.id)
        
        # 3. Create Optimized Route Header
        route = OptimizedRoute(
            organization_id=org_id,
            vehicle_id=vehicle_id,
            status="draft",
            total_distance_km=0.0, # To be calculated via Map API
            estimated_duration_min=len(pickups) * 15 # Rough estimate
        )
        RouteOptimizationRepository.create_route(db, route)
        db.flush() # Get route ID
        
        # 4. Create Waypoints
        for i, pickup in enumerate(sorted_pickups):
            waypoint = RouteWaypoint(
                optimized_route_id=route.id,
                stop_number=i + 1,
                waypoint_type="pickup",
                reference_id=pickup.id,
                latitude=pickup.latitude if hasattr(pickup, 'latitude') else 0.0,
                longitude=pickup.longitude if hasattr(pickup, 'longitude') else 0.0
            )
            RouteOptimizationRepository.add_waypoint(db, waypoint)
            
        db.commit()
        db.refresh(route)
        return route

    @staticmethod
    async def assign_route_to_driver(db: Session, route_id: int, driver_id: int):
        route = RouteOptimizationRepository.get_route_by_id(db, route_id)
        if route:
            route.driver_id = driver_id
            route.status = "assigned"
            db.commit()
        return route

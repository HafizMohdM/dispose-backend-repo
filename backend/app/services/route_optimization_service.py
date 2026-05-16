from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from datetime import datetime
import logging
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from app.repositories.route_optimization_repo import RouteOptimizationRepository
from app.models.route_optimization import OptimizedRoute, RouteWaypoint
from app.models.pickup import Pickup
from app.models.user import User
from app.api.v1.routes.route_schemas import RouteOptimizeRequest, OptimizedRouteResponse
from app.services.audit_service import log_event

logger = logging.getLogger(__name__)

class RouteOptimizationService:

    @staticmethod
    async def generate_optimized_route(
        db: Session, 
        org_id: int, 
        request: RouteOptimizeRequest
    ) -> OptimizedRoute:
        """
        Production-grade Route Optimization using Google OR-Tools (TSP)
        """
        # 1. Fetch pickups
        pickups = db.query(Pickup).filter(
            Pickup.id.in_(request.pickup_ids),
            Pickup.organization_id == org_id
        ).all()

        if not pickups:
            raise ValueError("No valid pickups found")

        # 2. Prepare locations (Depot + Pickups)
        locations = []
        pickup_map = {}  # index -> pickup

        # Add Depot (starting point)
        depot_lat = request.depot_latitude or 12.9716  # Default to Bangalore if not provided
        depot_lon = request.depot_longitude or 77.5946
        locations.append((depot_lat, depot_lon))

        # Add Pickups
        for i, p in enumerate(pickups):
            locations.append((p.latitude, p.longitude))
            pickup_map[i + 1] = p  # index 0 = depot

        num_locations = len(locations)

        # 3. Create Distance Matrix (Haversine distance)
        distance_matrix = RouteOptimizationService._create_distance_matrix(locations)

        # 4. Solve TSP using OR-Tools
        route_indices, total_distance_km, estimated_duration_min = \
            RouteOptimizationService._solve_tsp_or_tools(distance_matrix)

        # 5. Create Optimized Route in DB
        optimized_route = OptimizedRoute(
            organization_id=org_id,
            vehicle_id=request.vehicle_id,
            status="draft",
            total_distance_km=round(total_distance_km, 2),
            estimated_duration_min=estimated_duration_min,
            optimization_score=RouteOptimizationService._calculate_optimization_score(total_distance_km, len(pickups))
        )

        RouteOptimizationRepository.create_route(db, optimized_route)
        db.flush()

        # 6. Create Waypoints in optimized order
        for stop_number, location_index in enumerate(route_indices):
            if location_index == 0:  # Skip depot for now (can be added as first stop)
                continue

            pickup = pickup_map.get(location_index)
            if pickup:
                waypoint = RouteWaypoint(
                    optimized_route_id=optimized_route.id,
                    stop_number=stop_number,
                    waypoint_type="pickup",
                    reference_id=pickup.id,
                    latitude=pickup.latitude,
                    longitude=pickup.longitude
                )
                RouteOptimizationRepository.add_waypoint(db, waypoint)

        db.commit()
        db.refresh(optimized_route)

        log_event(
            db=db,
            user_id=None,  # System generated
            action="ROUTE_OPTIMIZED",
            org_id=org_id,
            metadata={
                "route_id": optimized_route.id,
                "pickup_count": len(pickups),
                "total_distance_km": total_distance_km,
                "estimated_duration_min": estimated_duration_min
            }
        )

        return optimized_route

    @staticmethod
    def _create_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
        """Create distance matrix using Haversine formula"""
        def haversine(lat1, lon1, lat2, lon2):
            from math import radians, sin, cos, sqrt, atan2
            R = 6371.0  # Earth radius in km
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c

        n = len(locations)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = int(haversine(
                        locations[i][0], locations[i][1],
                        locations[j][0], locations[j][1]
                    ) * 1000)  # meters
        return matrix

    @staticmethod
    def _solve_tsp_or_tools(distance_matrix: List[List[int]]) -> Tuple[List[int], float, int]:
        """Solve TSP using OR-Tools"""
        manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Setting parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(5)

        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            index = routing.Start(0)
            route = []
            total_distance = 0

            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)

            route.append(manager.IndexToNode(index))  # Return to start
            total_distance_km = total_distance / 1000.0
            estimated_min = int(total_distance_km * 2.5) + (len(route) * 8)  # Rough estimate

            return route, total_distance_km, estimated_min

        # Fallback
        return list(range(len(distance_matrix))), 0.0, len(distance_matrix) * 20

    @staticmethod
    def _calculate_optimization_score(distance_km: float, pickup_count: int) -> float:
        """Calculate optimization quality score (0-100)"""
        base_score = 85.0
        efficiency = min(100, max(40, 100 - (distance_km / pickup_count) * 8))
        return round((base_score + efficiency) / 2, 1)

    @staticmethod
    async def assign_route_to_driver(db: Session, route_id: int, driver_id: int):
        route = RouteOptimizationRepository.get_route_by_id(db, route_id)
        if route:
            route.driver_id = driver_id
            route.status = "assigned"
            db.commit()
            db.refresh(route)
        return route

    @staticmethod
    def get_active_routes(db: Session, org_id: int) -> List[OptimizedRoute]:
        """Fetch active, dispatched, or in_progress routes for the organization"""
        return RouteOptimizationRepository.get_active_routes(db, org_id)
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.trip import Trip, TripStatus
from app.models.pickup import Pickup, PickupStatus
from app.models.incident import Incident, IncidentStatus
from app.models.sustainability import EcoGoal

class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_vehicles_count(self, organization_id: int) -> int:
        return self.db.query(func.count(Vehicle.id)).filter(
            Vehicle.organization_id == organization_id,
            Vehicle.status == VehicleStatus.ACTIVE
        ).scalar() or 0

    def get_active_trips_count(self, organization_id: int) -> int:
        return self.db.query(func.count(Trip.id)).filter(
            Trip.organization_id == organization_id,
            Trip.status.in_([TripStatus.EN_ROUTE, TripStatus.ACTIVE_LOADING])
        ).scalar() or 0

    def get_total_waste_weight(self, organization_id: int) -> float:
        return self.db.query(func.coalesce(func.sum(Pickup.waste_weight), 0.0)).filter(
            Pickup.organization_id == organization_id,
            Pickup.status == PickupStatus.COMPLETED
        ).scalar()

    def get_active_incidents_count(self, organization_id: int) -> int:
        return self.db.query(func.count(Incident.id)).filter(
            Incident.organization_id == organization_id,
            Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS])
        ).scalar() or 0

    def get_completed_pickups_count(self, organization_id: int) -> int:
        return self.db.query(func.count(Pickup.id)).filter(
            Pickup.organization_id == organization_id,
            Pickup.status == PickupStatus.COMPLETED
        ).scalar() or 0

    def get_total_pickups_count(self, organization_id: int) -> int:
        return self.db.query(func.count(Pickup.id)).filter(
            Pickup.organization_id == organization_id
        ).scalar() or 0

    def get_eco_goals(self, organization_id: int):
        return self.db.query(EcoGoal).filter(
            EcoGoal.organization_id == organization_id
        ).all()

    def get_blocked_pickups_count(self, organization_id: int) -> int:
        return self.db.query(func.count(Pickup.id)).filter(
            Pickup.organization_id == organization_id,
            Pickup.status == PickupStatus.CANCELLED
        ).scalar() or 0

    def get_assignments_counts(self, organization_id: int):
        from app.models.pickup_assignment import PickupAssignment, AssignmentStatus
        total = self.db.query(func.count(PickupAssignment.id)).join(Pickup).filter(
            Pickup.organization_id == organization_id
        ).scalar() or 0
        
        completed = self.db.query(func.count(PickupAssignment.id)).join(Pickup).filter(
            Pickup.organization_id == organization_id,
            PickupAssignment.status == AssignmentStatus.COMPLETED
        ).scalar() or 0
        return total, completed

    def get_eco_goal_by_id(self, goal_id: int, organization_id: int) -> EcoGoal:
        return self.db.query(EcoGoal).filter(
            EcoGoal.id == goal_id,
            EcoGoal.organization_id == organization_id
        ).first()

    def update_eco_goal_atomic(self, goal_id: int, organization_id: int, new_value: float):
        from sqlalchemy import case
        self.db.query(EcoGoal).filter(
            EcoGoal.id == goal_id,
            EcoGoal.organization_id == organization_id
        ).update({
            EcoGoal.current_value: new_value,
            EcoGoal.is_completed: case(
                (new_value >= EcoGoal.target_value, True),
                else_=EcoGoal.is_completed
            )
        }, synchronize_session=False)
        self.db.commit()

    def get_sustainability_kpis(self, organization_id: int):
        # Database-level math engines tracking ESG sustainability KPIs
        # Hardcoded Logistic Math Constants: 2.5 for CO2, 1.2 for Energy
        result = self.db.query(
            func.coalesce(func.sum(Pickup.waste_weight), 0.0).label("total_weight"),
            (func.coalesce(func.sum(Pickup.waste_weight), 0.0) * 2.5).label("co2_saved"),
            (func.coalesce(func.sum(Pickup.waste_weight), 0.0) * 1.2).label("clean_energy")
        ).filter(
            Pickup.organization_id == organization_id,
            Pickup.status == PickupStatus.COMPLETED
        ).first()
        if not result:
            return 0.0, 0.0, 0.0
        return float(result.total_weight), float(result.co2_saved), float(result.clean_energy)

    def get_live_pickup_nodes(self, organization_id: int):
        return self.db.query(Pickup.id, Pickup.latitude, Pickup.longitude).filter(
            Pickup.organization_id == organization_id,
            Pickup.status.in_([PickupStatus.PENDING, PickupStatus.ASSIGNED, PickupStatus.IN_PROGRESS])
        ).all()

    def get_live_drivers_locations(self, organization_id: int):
        from app.models.fleet import LiveDriverLocation
        return self.db.query(LiveDriverLocation).filter(
            LiveDriverLocation.organization_id == organization_id
        ).all()

    def get_vehicle_fleet_health(self, organization_id: int):
        from app.models.vehicle import VehicleMaintenance, MaintenanceStatus
        total = self.db.query(func.count(Vehicle.id)).filter(Vehicle.organization_id == organization_id).scalar() or 0
        in_maintenance = self.db.query(func.count(Vehicle.id)).filter(Vehicle.organization_id == organization_id, Vehicle.status == VehicleStatus.MAINTENANCE).scalar() or 0
        critical_alerts = self.db.query(func.count(VehicleMaintenance.id)).filter(
            VehicleMaintenance.organization_id == organization_id, 
            VehicleMaintenance.status == MaintenanceStatus.SCHEDULED
        ).scalar() or 0
        return total, in_maintenance, critical_alerts

    def get_fleet_capacity(self, organization_id: int):
        total_capacity = self.db.query(func.sum(Vehicle.capacity_kg)).filter(
            Vehicle.organization_id == organization_id
        ).scalar() or 0.0
        utilized = self.db.query(func.sum(Pickup.waste_weight)).filter(
            Pickup.organization_id == organization_id,
            Pickup.status.in_([PickupStatus.IN_PROGRESS])
        ).scalar() or 0.0
        return total_capacity, utilized

    def get_todays_kpis(self, organization_id: int):
        from datetime import datetime, time
        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        
        pickups_today = self.db.query(func.count(Pickup.id)).filter(
            Pickup.organization_id == organization_id,
            Pickup.created_at >= today_start
        ).scalar() or 0
        
        completed_today = self.db.query(func.count(Pickup.id)).filter(
            Pickup.organization_id == organization_id,
            Pickup.status == PickupStatus.COMPLETED,
            Pickup.updated_at >= today_start
        ).scalar() or 0
        
        return pickups_today, completed_today

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.vehicle import Vehicle, VehicleAssignment, VehicleHealth, MaintenanceLog
from typing import List, Optional

class VehicleRepository:
    
    @staticmethod
    def create_vehicle(db: Session, vehicle: Vehicle) -> Vehicle:
        db.add(vehicle)
        # Initialize empty health record
        db.flush()
        health = VehicleHealth(vehicle_id=vehicle.id)
        db.add(health)
        return vehicle

    @staticmethod
    def get_vehicles_by_org(db: Session, organization_id: int) -> List[Vehicle]:
        return db.query(Vehicle).filter(Vehicle.organization_id == organization_id).all()

    @staticmethod
    def get_vehicle_by_id(db: Session, vehicle_id: int) -> Optional[Vehicle]:
        return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    @staticmethod
    def assign_driver(db: Session, vehicle_id: int, driver_id: int):
        # 1. Deactivate current active assignments for this vehicle
        db.query(VehicleAssignment).filter(
            and_(VehicleAssignment.vehicle_id == vehicle_id, VehicleAssignment.is_active == True)
        ).update({"is_active": False, "unassigned_at": datetime.utcnow()})
        
        # 2. Deactivate any active vehicle assignments for this driver
        db.query(VehicleAssignment).filter(
            and_(VehicleAssignment.driver_id == driver_id, VehicleAssignment.is_active == True)
        ).update({"is_active": False, "unassigned_at": datetime.utcnow()})
        
        # 3. Create new assignment
        assignment = VehicleAssignment(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            is_active=True
        )
        db.add(assignment)
        return assignment

    @staticmethod
    def get_active_assignment(db: Session, driver_id: int) -> Optional[VehicleAssignment]:
        return db.query(VehicleAssignment).filter(
            and_(VehicleAssignment.driver_id == driver_id, VehicleAssignment.is_active == True)
        ).first()

    @staticmethod
    def create_maintenance_log(db: Session, log: MaintenanceLog) -> MaintenanceLog:
        db.add(log)
        return log

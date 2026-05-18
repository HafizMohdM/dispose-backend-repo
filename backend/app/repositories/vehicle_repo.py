from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.vehicle import Vehicle, VehicleAssignment, VehicleStatus

class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, vehicle_id: int, organization_id: int) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == organization_id
        ).first()

    def get_by_registration_number(self, registration_number: str, organization_id: int) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(
            Vehicle.registration_number == registration_number,
            Vehicle.organization_id == organization_id
        ).first()

    def get_all(self, organization_id: int, skip: int = 0, limit: int = 100) -> List[Vehicle]:
        return self.db.query(Vehicle).filter(
            Vehicle.organization_id == organization_id,
            Vehicle.status != VehicleStatus.DELETED
        ).offset(skip).limit(limit).all()

    def create(self, vehicle: Vehicle) -> Vehicle:
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def update(self, vehicle: Vehicle) -> Vehicle:
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def soft_delete(self, vehicle: Vehicle) -> Vehicle:
        vehicle.status = VehicleStatus.DELETED
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def get_active_assignment(self, vehicle_id: int) -> Optional[VehicleAssignment]:
        return self.db.query(VehicleAssignment).filter(
            VehicleAssignment.vehicle_id == vehicle_id,
            VehicleAssignment.status == "ACTIVE"
        ).first()

    def get_active_assignment_by_driver(self, driver_id: int) -> Optional[VehicleAssignment]:
        return self.db.query(VehicleAssignment).filter(
            VehicleAssignment.driver_id == driver_id,
            VehicleAssignment.status == "ACTIVE"
        ).first()

    def create_assignment(self, assignment: VehicleAssignment) -> VehicleAssignment:
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

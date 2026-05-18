from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime
from typing import List

from app.models.vehicle import Vehicle, VehicleAssignment, VehicleStatus, VehicleMaintenance, MaintenanceStatus
from app.models.driver import Driver, DriverAvailability
from app.utils.enums import DriverAvailabilityStatus
from app.repositories.vehicle_repo import VehicleRepository
from app.api.v1.vehicles.vehicle_schemas import VehicleCreate, VehicleUpdate, VehicleMaintenanceCreate

class VehicleService:
    def __init__(self, db: Session):
        self.db = db
        self.vehicle_repo = VehicleRepository(db)

    def create_vehicle(self, organization_id: int, vehicle_data: VehicleCreate) -> Vehicle:
        existing_vehicle = self.vehicle_repo.get_by_registration_number(
            vehicle_data.registration_number, organization_id
        )
        if existing_vehicle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle with this registration number already exists."
            )

        new_vehicle = Vehicle(
            organization_id=organization_id,
            **vehicle_data.dict()
        )
        return self.vehicle_repo.create(new_vehicle)

    def get_vehicle(self, vehicle_id: int, organization_id: int) -> Vehicle:
        vehicle = self.vehicle_repo.get_by_id(vehicle_id, organization_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found."
            )
        return vehicle

    def list_vehicles(self, organization_id: int, skip: int = 0, limit: int = 100) -> List[Vehicle]:
        return self.vehicle_repo.get_all(organization_id, skip, limit)

    def update_vehicle(self, vehicle_id: int, organization_id: int, update_data: VehicleUpdate) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id, organization_id)
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(vehicle, key, value)
            
        return self.vehicle_repo.update(vehicle)

    def delete_vehicle(self, vehicle_id: int, organization_id: int):
        vehicle = self.get_vehicle(vehicle_id, organization_id)
        
        # A Vehicle cannot be deleted if it is currently assigned to an active driver or has an ACTIVE status
        active_assignment = self.vehicle_repo.get_active_assignment(vehicle_id)
        if active_assignment or vehicle.status == VehicleStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a vehicle that is assigned to an active driver or has an ACTIVE status."
            )
            
        self.vehicle_repo.soft_delete(vehicle)

    def assign_driver(self, vehicle_id: int, driver_id: int, organization_id: int, actor_user_id: int, ip_address: str = None) -> VehicleAssignment:
        # Check if vehicle exists
        vehicle = self.get_vehicle(vehicle_id, organization_id)
        
        # Check if driver exists and belongs to the same organization
        driver = self.db.query(Driver).filter(
            Driver.id == driver_id,
            Driver.organization_id == organization_id
        ).first()
        
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found."
            )

        # Check if the target vehicle is already occupied
        vehicle_assignment = self.vehicle_repo.get_active_assignment(vehicle_id)
        if vehicle_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle is already occupied by an active driver."
            )
            
        # Check if the driver is already actively driving another vehicle
        driver_assignment = self.vehicle_repo.get_active_assignment_by_driver(driver_id)
        if driver_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driver is already actively driving another vehicle."
            )

        # Retrieve DriverAvailability
        driver_availability = self.db.query(DriverAvailability).filter(
            DriverAvailability.driver_id == driver_id
        ).first()

        try:
            # The /assign-driver endpoint must run inside an atomic transaction block.
            # Begin a nested transaction (savepoint)
            with self.db.begin_nested():
                # Update the Vehicle.status to ACTIVE
                vehicle.status = VehicleStatus.ACTIVE
                
                # Set the driver's DriverAvailability.status to BUSY or keep it matching
                if driver_availability:
                    driver_availability.status = DriverAvailabilityStatus.BUSY
                    driver_availability.is_on_duty = True
                else:
                    driver_availability = DriverAvailability(
                        driver_id=driver_id,
                        status=DriverAvailabilityStatus.BUSY,
                        is_on_duty=True
                    )
                    self.db.add(driver_availability)

                # Insert a new record into the VehicleAssignment table
                new_assignment = VehicleAssignment(
                    vehicle_id=vehicle_id,
                    driver_id=driver_id,
                    is_active=True,
                    assigned_at=datetime.utcnow()
                )
                self.db.add(new_assignment)
                
            self.db.commit()
            self.db.refresh(new_assignment)
            
            from app.services.audit_service import log_event
            log_event(
                self.db,
                actor_user_id,
                "ADMIN_VEHICLE_ASSIGNED",
                org_id=organization_id,
                metadata={
                    "target_user_id": driver_id,
                    "actor_user_id": actor_user_id,
                    "org_id": organization_id,
                    "vehicle_id": vehicle_id,
                    "ip_address": ip_address
                }
            )
            return new_assignment
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to assign driver: {str(e)}"
            )

    def unassign_driver(self, vehicle_id: int, organization_id: int, actor_user_id: int, ip_address: str = None):
        vehicle = self.get_vehicle(vehicle_id, organization_id)
        
        active_assignment = self.vehicle_repo.get_active_assignment(vehicle_id)
        if not active_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active driver assignment found for this vehicle."
            )
            
        driver_availability = self.db.query(DriverAvailability).filter(
            DriverAvailability.driver_id == active_assignment.driver_id
        ).first()

        try:
            with self.db.begin_nested():
                active_assignment.is_active = False
                active_assignment.unassigned_at = datetime.utcnow()
                
                vehicle.status = VehicleStatus.INACTIVE
                
                if driver_availability:
                    driver_availability.status = DriverAvailabilityStatus.AVAILABLE
                    
            self.db.commit()
            
            from app.services.audit_service import log_event
            log_event(
                self.db,
                actor_user_id,
                "ADMIN_VEHICLE_UNASSIGNED",
                org_id=organization_id,
                metadata={
                    "target_user_id": active_assignment.driver_id,
                    "actor_user_id": actor_user_id,
                    "org_id": organization_id,
                    "vehicle_id": vehicle_id,
                    "ip_address": ip_address
                }
            )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to unassign driver: {str(e)}"
            )

    def create_maintenance(self, vehicle_id: int, organization_id: int, request: VehicleMaintenanceCreate) -> VehicleMaintenance:
        vehicle = self.get_vehicle(vehicle_id, organization_id)
        new_maintenance = VehicleMaintenance(
            vehicle_id=vehicle_id,
            organization_id=organization_id,
            description=request.description,
            cost=request.cost,
            scheduled_date=request.scheduled_date,
            status=MaintenanceStatus.SCHEDULED
        )
        self.db.add(new_maintenance)
        self.db.commit()
        self.db.refresh(new_maintenance)
        return new_maintenance

    def list_maintenances(self, organization_id: int, skip: int = 0, limit: int = 50) -> List[VehicleMaintenance]:
        return self.db.query(VehicleMaintenance).filter(
            VehicleMaintenance.organization_id == organization_id
        ).offset(skip).limit(limit).all()

    def get_fleet_health(self, organization_id: int) -> dict:
        total_vehicles = self.db.query(Vehicle).filter(Vehicle.organization_id == organization_id).count()
        active_vehicles = self.db.query(Vehicle).filter(Vehicle.organization_id == organization_id, Vehicle.status == VehicleStatus.ACTIVE).count()
        in_maintenance = self.db.query(Vehicle).filter(Vehicle.organization_id == organization_id, Vehicle.status == VehicleStatus.MAINTENANCE).count()
        inactive_vehicles = self.db.query(Vehicle).filter(Vehicle.organization_id == organization_id, Vehicle.status == VehicleStatus.INACTIVE).count()
        
        # Count open high/critical incidents or similar metrics for critical alerts
        from app.models.incident import Incident, IncidentStatus, IncidentSeverity
        critical_alerts = self.db.query(Incident).filter(
            Incident.organization_id == organization_id,
            Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]),
            Incident.severity.in_([IncidentSeverity.HIGH, IncidentSeverity.CRITICAL])
        ).count()

        return {
            "total_vehicles": total_vehicles,
            "active_vehicles": active_vehicles,
            "in_maintenance": in_maintenance,
            "inactive_vehicles": inactive_vehicles,
            "critical_alerts": critical_alerts
        }

from sqlalchemy.orm import Session, joinedload
from app.models.pickup import Pickup, PickupStatus
from app.models.pickup_assignment import PickupAssignment, AssignmentStatus
from datetime import datetime

class PickupRepository:
    
    @staticmethod
    def create_pickup(db: Session, pickup: Pickup) -> Pickup:
        db.add(pickup)
        # Flush to get the ID without committing the outer transaction
        db.flush()
        return pickup
        
    @staticmethod
    def get_pickup_by_id(db: Session, pickup_id: int) -> Pickup:
        return db.query(Pickup).options(
            joinedload(Pickup.assignments)
        ).filter(Pickup.id == pickup_id).first()

    @staticmethod
    def list_org_pickups(db: Session, organization_id: int, status: PickupStatus = None) -> list[Pickup]:
        query = db.query(Pickup).options(
            joinedload(Pickup.assignments)
        ).filter(Pickup.organization_id == organization_id)
        if status:
            query = query.filter(Pickup.status == status)
        return query.order_by(Pickup.created_at.desc()).all()

    @staticmethod
    def list_driver_pickups(db: Session, driver_id: int, status: AssignmentStatus = None) -> list[Pickup]:
        query = db.query(Pickup).join(PickupAssignment).options(
            joinedload(Pickup.assignments)
        ).filter(PickupAssignment.driver_id == driver_id)
        if status:
            query = query.filter(PickupAssignment.status == status)
        return query.order_by(Pickup.scheduled_at.desc(), Pickup.created_at.desc()).all()

    @staticmethod
    def list_all_pickups(db: Session, status: PickupStatus = None) -> list[Pickup]:
        query = db.query(Pickup).options(
            joinedload(Pickup.assignments)
        )
        if status:
            query = query.filter(Pickup.status == status)
        return query.order_by(Pickup.created_at.desc()).all()

    @staticmethod
    def update_pickup_status(db: Session, pickup_id: int, status: PickupStatus) -> Pickup:
        pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
        if pickup:
            pickup.status = status
            if status == PickupStatus.COMPLETED:
                pickup.completed_at = datetime.utcnow()
            db.flush()
        return pickup

    @staticmethod
    def assign_driver(db: Session, pickup_id: int, driver_id: int) -> PickupAssignment:
        assignment = PickupAssignment(
            pickup_id=pickup_id,
            driver_id=driver_id,
            status=AssignmentStatus.ASSIGNED
        )
        db.add(assignment)
        db.flush()
        return assignment

    @staticmethod
    def get_with_lock(db: Session, pickup_id: int) -> Pickup:
        return db.query(Pickup).options(
            joinedload(Pickup.assignments)
        ).filter(Pickup.id == pickup_id).with_for_update().first()

    @staticmethod
    def remove_assignment(db: Session, pickup_id: int, driver_id: int):
        assignment = db.query(PickupAssignment).filter(
            PickupAssignment.pickup_id == pickup_id,
            PickupAssignment.driver_id == driver_id
        ).first()
        if assignment:
            db.delete(assignment)
            db.flush()

    @staticmethod
    def update_schedule(db: Session, pickup_id: int, scheduled_at: datetime) -> Pickup:
        pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
        if pickup:
            pickup.scheduled_at = scheduled_at
            db.flush()
        return pickup

    @staticmethod
    def update_completion(db: Session, pickup_id: int, actual_weight: float) -> Pickup:
        pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
        if pickup:
            pickup.status = PickupStatus.COMPLETED
            pickup.completed_at = datetime.utcnow()
            pickup.waste_weight = actual_weight
            db.flush()
        return pickup

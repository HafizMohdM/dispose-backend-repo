from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.repositories.pickup_repo import PickupRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.models.pickup import Pickup, PickupStatus
from app.models.subscription import SubscriptionStatus
from app.models.pickup_assignment import AssignmentStatus
from app.api.v1.pickups.pickup_schemas import PickupCreateRequest, PickupUpdateStatusRequest

class PickupService:

    @staticmethod
    def create_pickup(db: Session, organization, request: PickupCreateRequest) -> Pickup:
        # 1. Fetch ACTIVE subscription for organization
        sub = SubscriptionRepository.get_active_subscription(db, organization.id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active subscription found. Please subscribe to a plan.")
        
        # 2. Validate not expired
        if datetime.utcnow() > sub.end_date:
            SubscriptionRepository.update_subscription_status(db, sub.id, SubscriptionStatus.EXPIRED)
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription has expired.")

        # 3. Lock subscription_usage row and safely increment usage using the existing atomic validator
        try:
            # Reusing the tested atomic validator from the subscription module.
            from app.services.subscription_service import SubscriptionService
            incremented_usage = SubscriptionService.validate_and_increment_usage(
                db=db, 
                subscription_id=sub.id, 
                pickups=1, 
                weight=request.waste_weight, 
                drivers=0
            ) 
        except HTTPException as e:
            raise e
        except Exception as e:
            # If the atomic increment fails for an unforeseen reason, rollback everything to be safe
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process pickup due to a system error.")

        # 4. Create the pickup since usage was validated
        new_pickup = Pickup(
            organization_id=organization.id,
            subscription_id=sub.id,
            waste_type=request.waste_type,
            waste_weight=request.waste_weight,
            address=request.address,
            latitude=request.latitude,
            longitude=request.longitude,
            status=PickupStatus.PENDING,
            scheduled_at=request.scheduled_at
        )

        created_pickup = PickupRepository.create_pickup(db, new_pickup)
        
        # 5. Commit atomic transaction
        db.commit()
        db.refresh(created_pickup)
        
        return created_pickup

    @staticmethod
    def list_pickups_for_org(db: Session, organization_id: int, p_status: PickupStatus = None):
        return PickupRepository.list_org_pickups(db, organization_id, p_status)

    @staticmethod
    def list_pickups_for_driver(db: Session, driver_id: int, a_status: AssignmentStatus = None):
        return PickupRepository.list_driver_pickups(db, driver_id, a_status)

    @staticmethod
    def list_all_pickups(db: Session, p_status: PickupStatus = None):
        return PickupRepository.list_all_pickups(db, p_status)

    @staticmethod
    def get_pickup_by_id(db: Session, pickup_id: int):
        pickup = PickupRepository.get_pickup_by_id(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
        return pickup

    @staticmethod
    def update_pickup_status(db: Session, pickup_id: int, request: PickupUpdateStatusRequest, user, is_admin: bool):
        pickup = PickupService.get_pickup_by_id(db, pickup_id)
        
        # Validate permissions depending on the operation
        if not is_admin:
            # Validate driver owns the assignment if they are trying to mark it complete
            if request.status in [PickupStatus.IN_PROGRESS, PickupStatus.COMPLETED]:
                is_assigned = any(assignment.driver_id == user.id for assignment in pickup.assignments)
                if not is_assigned:
                    raise HTTPException(status_code=403, detail="You are not assigned to this pickup.")

        old_status = pickup.status
        new_status = request.status

        # Strict State Machine Transition Rules
        valid_transitions = {
            PickupStatus.PENDING: [PickupStatus.ASSIGNED, PickupStatus.CANCELLED],
            PickupStatus.ASSIGNED: [PickupStatus.IN_PROGRESS, PickupStatus.CANCELLED],
            PickupStatus.IN_PROGRESS: [PickupStatus.COMPLETED, PickupStatus.CANCELLED],
            PickupStatus.COMPLETED: [],
            PickupStatus.CANCELLED: []
        }

        if new_status not in valid_transitions.get(old_status, []):
            raise HTTPException(status_code=400, detail=f"Invalid transition from {old_status} to {new_status}")

        # If cancelled early, ideally we return the usage back. Note: If we do this, we need to lock the usage row again.
        if new_status == PickupStatus.CANCELLED and old_status != PickupStatus.COMPLETED:
            from app.services.subscription_service import SubscriptionService
            # Decrement securely
            try:
                SubscriptionService.validate_and_increment_usage(
                    db=db, 
                    subscription_id=pickup.subscription_id, 
                    pickups=-1, 
                    weight=-pickup.waste_weight, 
                    drivers=0
                )
            except Exception:
                # ignore decrement errors if subscription is missing/deleted
                pass

        updated_pickup = PickupRepository.update_pickup_status(db, pickup_id, new_status)
        db.commit()
        db.refresh(updated_pickup)
        
        return updated_pickup

    @staticmethod
    def assign_driver(db: Session, pickup_id: int, driver_id: int):
        # 1. Validate pickup exists and is pending
        pickup = PickupService.get_pickup_by_id(db, pickup_id)
        if pickup.status != PickupStatus.PENDING:
            raise HTTPException(status_code=400, detail="Pickup must be PENDING to be assigned.")
            
        # 2. Assign Driver
        assignment = PickupRepository.assign_driver(db, pickup_id, driver_id)
        
        # 3. Transition Pickup state to ASSIGNED
        pickup.status = PickupStatus.ASSIGNED
        
        db.commit()
        db.refresh(pickup)
        return assignment

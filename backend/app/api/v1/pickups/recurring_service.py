from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.models.recurring_pickup import RecurringPickup, RecurringFrequency
from app.models.pickup import Pickup, PickupStatus, PickupPriority
from app.api.v1.pickups.recurring_schemas import RecurringPickupCreateRequest
from app.repositories.recurring_pickup_repo import RecurringPickupRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.repositories.pickup_repo import PickupRepository
from app.repositories.pickup_activity_repo import PickupActivityRepository
from app.models.pickup_activity import ActivityType

logger = logging.getLogger(__name__)

class RecurringPickupService:
    @staticmethod
    def create_recurring_pickup(db: Session, org_id: int, request: RecurringPickupCreateRequest) -> RecurringPickup:
        recurring_pickup = RecurringPickup(
            organization_id=org_id,
            waste_type=request.waste_type,
            waste_weight=request.waste_weight,
            address=request.address,
            latitude=request.latitude,
            longitude=request.longitude,
            frequency=request.frequency,
            next_run_at=request.next_run_at
        )
        return RecurringPickupRepository.create(db, recurring_pickup)

    @staticmethod
    def spawn_due_pickups(db: Session):
        due_pickups = RecurringPickupRepository.get_due_recurring_pickups(db)
        
        for rule in due_pickups:
            try:
                # 1. Fetch Organization Subscription
                sub = SubscriptionRepository.get_active_subscription(db, rule.organization_id)
                if not sub:
                    logger.error(f"RecurringPickup {rule.id}: No active subscription for org {rule.organization_id}")
                    continue
                
                # 2. Check and Increment Plan Usage (Billing Enforcer)
                try:
                    SubscriptionService.validate_and_increment_usage(
                        db=db, 
                        subscription_id=sub.id, 
                        pickups=1, 
                        weight=rule.waste_weight, 
                        drivers=0
                    )
                except Exception as e:
                    db.rollback()
                    logger.error(f"RecurringPickup {rule.id}: Quota exceeded for org {rule.organization_id} - {str(e)}")
                    continue
                
                # 3. Spawn Pickup
                new_pickup = Pickup(
                    organization_id=rule.organization_id,
                    subscription_id=sub.id,
                    waste_type=rule.waste_type,
                    waste_weight=rule.waste_weight,
                    address=rule.address,
                    latitude=rule.latitude,
                    longitude=rule.longitude,
                    status=PickupStatus.PENDING,
                    priority=PickupPriority.NORMAL
                )
                PickupRepository.create_pickup(db, new_pickup)
                
                # 4. Log Activity
                PickupActivityRepository.log_activity(
                    db=db,
                    pickup_id=new_pickup.id,
                    user_id=None, # System
                    activity_type=ActivityType.CREATED,
                    description="Generated via Recurring Schedule."
                )
                
                # 5. Update next_run_at
                if rule.frequency == RecurringFrequency.DAILY:
                    rule.next_run_at += timedelta(days=1)
                elif rule.frequency == RecurringFrequency.WEEKLY:
                    rule.next_run_at += timedelta(weeks=1)
                elif rule.frequency == RecurringFrequency.MONTHLY:
                    rule.next_run_at += timedelta(days=30)
                    
                db.commit()
                logger.info(f"Successfully spawned Pickup {new_pickup.id} from RecurringPickup {rule.id}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to spawn pickup for rule {rule.id}: {str(e)}")

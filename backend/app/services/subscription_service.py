from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.repositories.subscription_repo import SubscriptionRepository
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.subscription_usage import SubscriptionUsage
from app.models.subscription_plan import BillingCycle

class SubscriptionService:
    @staticmethod
    def create_plan(db: Session, plan_data):
        from app.models.subscription_plan import SubscriptionPlan
        db_plan = SubscriptionPlan(**plan_data.model_dump())
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
        return db_plan

    @staticmethod
    def list_plans(db: Session):
        return SubscriptionRepository.list_visible_plans(db)

    @staticmethod
    def update_plan(db: Session, plan_id: int, plan_data):
        plan = SubscriptionRepository.get_plan_by_id(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        update_data = plan_data.model_dump(exclude_unset=True)
        updated_plan = SubscriptionRepository.update_plan(db, plan_id, update_data)
        db.commit()
        db.refresh(updated_plan)
        return updated_plan

    @staticmethod
    def delete_plan(db: Session, plan_id: int):
        plan = SubscriptionRepository.get_plan_by_id(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        # Optional: Check if the plan is currently being used by any active subscriptions
        # before allowing deletion, or just soft-delete by setting is_active/is_visible to False.
        # For a hard delete as requested:
        deleted = SubscriptionRepository.delete_plan(db, plan_id)
        if deleted:
            db.commit()
            return {"message": "Plan deleted successfully"}
        raise HTTPException(status_code=400, detail="Failed to delete plan")

    @staticmethod
    def subscribe(db: Session, organization, plan_id: int):
        # 1. Validate plan
        plan = SubscriptionRepository.get_plan_by_id(db, plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found or inactive")
        
        # 2. Validate eligibility
        if plan.category_type.value == "APARTMENT":
            total_units = getattr(organization, "total_units", 0)
            if plan.max_units and total_units > plan.max_units:
                raise HTTPException(status_code=400, detail="Organization exceeds max units for this plan")
        
        elif plan.category_type.value == "HOUSEHOLD":
            total_members = getattr(organization, "total_members", 0)
            if plan.max_members and total_members > plan.max_members:
                raise HTTPException(status_code=400, detail="Organization exceeds max members for this plan")

        # 3. Ensure no ACTIVE subscription exists
        active_sub = SubscriptionRepository.get_active_subscription(db, organization.id)
        if active_sub:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization already has an active subscription")

        # 4. Create PENDING subscription
        now = datetime.utcnow()
        if plan.billing_cycle == BillingCycle.MONTHLY:
            end_date = now + timedelta(days=30)
        else: # YEARLY
            end_date = now + timedelta(days=365)
            
        new_sub = Subscription(
            organization_id=organization.id,
            plan_id=plan.id,
            start_date=now,
            end_date=end_date,
            status=SubscriptionStatus.PENDING,
            auto_renew=True
        )
        SubscriptionRepository.create_subscription(db, new_sub)
        
        # 5. Simulate payment success -> Activate subscription
        new_sub.status = SubscriptionStatus.ACTIVE
        
        # 6. Create usage record
        usage = SubscriptionUsage(subscription_id=new_sub.id)
        SubscriptionRepository.create_usage_record(db, usage)
        
        # 7. Commit transaction
        db.commit()
        db.refresh(new_sub)
        return new_sub

    @staticmethod
    def cancel_subscription(db: Session, organization_id: int):
        sub = SubscriptionRepository.get_active_subscription(db, organization_id)
        if not sub:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        if sub.status == SubscriptionStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Subscription is already cancelled")
            
        sub = SubscriptionRepository.update_subscription_status(
            db, 
            sub.id, 
            SubscriptionStatus.CANCELLED,
            cancelled_at=datetime.utcnow()
        )
        db.commit()
        db.refresh(sub)
        return sub

    @staticmethod
    def upgrade_subscription(db: Session, organization_id: int, new_plan_id: int):
        old_sub = SubscriptionRepository.get_active_subscription(db, organization_id)
        if not old_sub:
            raise HTTPException(status_code=404, detail="No active subscription found to upgrade")
            
        new_plan = SubscriptionRepository.get_plan_by_id(db, new_plan_id)
        if not new_plan or not new_plan.is_active:
            raise HTTPException(status_code=400, detail="New plan not found or inactive")
            
        old_sub.status = SubscriptionStatus.EXPIRED
        db.flush()
        
        now = datetime.utcnow()
        if new_plan.billing_cycle == BillingCycle.MONTHLY:
            end_date = now + timedelta(days=30)
        else:
            end_date = now + timedelta(days=365)
            
        new_sub = Subscription(
            organization_id=organization_id,
            plan_id=new_plan.id,
            start_date=now,
            end_date=end_date,
            status=SubscriptionStatus.ACTIVE,
            auto_renew=True,
            upgraded_from_id=old_sub.id
        )
        SubscriptionRepository.create_subscription(db, new_sub)
        
        new_usage = SubscriptionUsage(subscription_id=new_sub.id)
        SubscriptionRepository.create_usage_record(db, new_usage)
        
        db.commit()
        db.refresh(new_sub)
        return new_sub

    @staticmethod
    def validate_and_increment_usage(db: Session, subscription_id: int, pickups: int = 0, weight: float = 0.0, drivers: int = 0):
        # Lock usage row
        sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not sub or sub.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="Active subscription required")
            
        if datetime.utcnow() > sub.end_date:
            sub.status = SubscriptionStatus.EXPIRED
            db.commit()
            raise HTTPException(status_code=403, detail="Subscription has expired")
            
        incremented_usage = SubscriptionRepository.increment_usage(db, subscription_id, pickups, weight, drivers)
        if not incremented_usage:
            raise HTTPException(status_code=404, detail="Usage record not found")
            
        if sub.plan.pickup_limit > 0 and incremented_usage.pickups_used > sub.plan.pickup_limit:
            db.rollback() # Usage was incremented inside flush, so rollback
            raise HTTPException(status_code=403, detail="Pickup limit exceeded")
            
        if sub.plan.waste_weight_limit > 0 and incremented_usage.waste_weight_used > sub.plan.waste_weight_limit:
            db.rollback()
            raise HTTPException(status_code=403, detail="Waste weight limit exceeded")
            
        db.commit()
        db.refresh(incremented_usage)
        return incremented_usage

    @staticmethod
    def get_my_subscription(db: Session, organization_id: int):
        sub = SubscriptionRepository.get_latest_subscription(db, organization_id)
        if not sub:
            raise HTTPException(status_code=404, detail="No subscription found")
        return sub

    @staticmethod
    def get_usage(db: Session, subscription_id: int):
        usage = SubscriptionRepository.get_usage(db, subscription_id)
        if not usage:
            raise HTTPException(status_code=404, detail="Usage record not found")
        return usage

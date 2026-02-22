from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.subscription_usage import SubscriptionUsage

class SubscriptionRepository:
    @staticmethod
    def get_plan_by_id(db: Session, plan_id: int) -> SubscriptionPlan:
        return db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()

    @staticmethod
    def list_visible_plans(db: Session) -> list[SubscriptionPlan]:
        return db.query(SubscriptionPlan).filter(
            SubscriptionPlan.is_visible == True,
            SubscriptionPlan.is_active == True
        ).all()

    @staticmethod
    def update_plan(db: Session, plan_id: int, update_data: dict) -> SubscriptionPlan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if plan:
            for key, value in update_data.items():
                setattr(plan, key, value)
            db.flush()
        return plan

    @staticmethod
    def delete_plan(db: Session, plan_id: int) -> bool:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if plan:
            db.delete(plan)
            db.flush()
            return True
        return False

    @staticmethod
    def create_subscription(db: Session, subscription: Subscription) -> Subscription:
        db.add(subscription)
        db.flush()
        return subscription

    @staticmethod
    def get_active_subscription(db: Session, organization_id: int) -> Subscription:
        return db.query(Subscription).filter(
            Subscription.organization_id == organization_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()

    @staticmethod
    def get_latest_subscription(db: Session, organization_id: int) -> Subscription:
        return db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).order_by(Subscription.created_at.desc()).first()

    @staticmethod
    def update_subscription_status(db: Session, subscription_id: int, status: SubscriptionStatus, cancelled_at=None) -> Subscription:
        sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if sub:
            sub.status = status
            if cancelled_at:
                sub.cancelled_at = cancelled_at
            db.flush()
        return sub

    @staticmethod
    def create_usage_record(db: Session, usage: SubscriptionUsage) -> SubscriptionUsage:
        db.add(usage)
        db.flush()
        return usage

    @staticmethod
    def get_usage(db: Session, subscription_id: int) -> SubscriptionUsage:
        return db.query(SubscriptionUsage).filter(SubscriptionUsage.subscription_id == subscription_id).first()

    @staticmethod
    def increment_usage(db: Session, subscription_id: int, pickups: int = 0, weight: float = 0.0, drivers: int = 0) -> SubscriptionUsage:
        usage = db.query(SubscriptionUsage).filter(
            SubscriptionUsage.subscription_id == subscription_id
        ).with_for_update().first()
        
        if usage:
            usage.pickups_used += pickups
            usage.waste_weight_used += weight
            usage.drivers_used += drivers
            db.flush()
        return usage

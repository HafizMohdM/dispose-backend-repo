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
        
        # 5. Create Invoice for the subscription
        from app.repositories.payment_repo import PaymentRepository
        invoice = PaymentRepository.create_invoice(
            db=db,
            organization_id=organization.id,
            amount=plan.price,
            due_date=now,
            subscription_id=new_sub.id
        )
        
        # 6. Log the audit event for subscription initiation
        from app.services.audit_service import AuditService
        audit_svc = AuditService(db)
        audit_svc.log_action(
            user_id=organization.id, # Using org id or placeholder if user context missing
            action="subscription.initiated",
            org_id=organization.id,
            meta={"plan_id": plan.id, "invoice_id": str(invoice.id)}
        )
        
        # 7. Commit transaction
        db.commit()
        db.refresh(new_sub)
        return new_sub

    @staticmethod
    def cancel_subscription(db: Session, organization_id: int):
        sub = db.query(Subscription).filter(
            Subscription.organization_id == organization_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE, SubscriptionStatus.PENDING])
        ).order_by(Subscription.created_at.desc()).first()
        
        if not sub:
            raise HTTPException(status_code=404, detail="No active or pending subscription found")
        
        if sub.status == SubscriptionStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Subscription is already cancelled")
            
        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = datetime.utcnow()

        # Phase 3 Hardening: Auto-cancel orphaned invoices & payments to stop ghost checkouts
        from app.models.invoice import Invoice, InvoiceStatus
        from app.models.payment import Payment, PaymentStatus
        
        pending_invoices = db.query(Invoice).filter(
            Invoice.subscription_id == sub.id,
            Invoice.status == InvoiceStatus.PENDING
        ).all()
        
        for inv in pending_invoices:
            inv.status = InvoiceStatus.CANCELLED
            # Also cancel initiated payments trying to pay this invoice
            initiated_payments = db.query(Payment).filter(
                Payment.invoice_id == inv.id,
                Payment.status == PaymentStatus.INITIATED
            ).all()
            for p in initiated_payments:
                p.status = PaymentStatus.CANCELLED

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
            
        # We do NOT expire the old sub here. We keep it rolling so they don't lose access.
        # The webhook processor will auto-expire it once they successfully pay the new invoice.
        
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
            status=SubscriptionStatus.PENDING,
            auto_renew=True,
            upgraded_from_id=old_sub.id
        )
        SubscriptionRepository.create_subscription(db, new_sub)
        
        # 5. Create Invoice for the upgrade
        from app.repositories.payment_repo import PaymentRepository
        invoice = PaymentRepository.create_invoice(
            db=db,
            organization_id=organization_id,
            amount=new_plan.price,
            due_date=now + timedelta(days=7),
            subscription_id=new_sub.id
        )
        
        # 6. Log the audit event
        from app.services.audit_service import AuditService
        audit_svc = AuditService(db)
        audit_svc.log_action(
            user_id=organization_id,
            action="subscription.upgrade_initiated",
            org_id=organization_id,
            meta={"old_plan_id": old_sub.plan_id, "new_plan_id": new_plan.id, "invoice_id": str(invoice.id)}
        )
        
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
    @staticmethod
    def renew_expired_subscriptions(db: Session):
        now = datetime.utcnow()
        expiring_subs = SubscriptionRepository.get_expiring_subscriptions(db, now)
        
        from app.repositories.payment_repo import PaymentRepository
        from app.services.audit_service import AuditService
        
        audit_svc = AuditService(db)
        renewed_count = 0
        
        for sub in expiring_subs:
            # Mark old as EXPIRED
            sub.status = SubscriptionStatus.EXPIRED
            
            if not sub.auto_renew:
                continue
                
            # Generate replacement subscription
            if sub.plan.billing_cycle == BillingCycle.MONTHLY:
                end_date_new = now + timedelta(days=30)
            else:
                end_date_new = now + timedelta(days=365)
                
            new_sub = Subscription(
                organization_id=sub.organization_id,
                plan_id=sub.plan_id,
                start_date=now,
                end_date=end_date_new,
                status=SubscriptionStatus.PENDING,
                auto_renew=True
            )
            SubscriptionRepository.create_subscription(db, new_sub)
            
            # Generate new Invoice
            invoice = PaymentRepository.create_invoice(
                db=db,
                organization_id=sub.organization_id,
                amount=sub.plan.price,
                due_date=now + timedelta(days=7), # 7 day grace period
                subscription_id=new_sub.id
            )
            
            audit_svc.log_action(
                user_id=sub.organization_id,
                action="subscription.renewed",
                org_id=sub.organization_id,
                meta={"old_sub_id": sub.id, "new_sub_id": new_sub.id, "invoice_id": str(invoice.id)}
            )
            renewed_count += 1
            
        db.commit()
        return {"processed": len(expiring_subs), "renewed": renewed_count}

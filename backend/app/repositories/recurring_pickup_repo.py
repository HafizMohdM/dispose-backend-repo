from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.models.recurring_pickup import RecurringPickup

class RecurringPickupRepository:
    @staticmethod
    def create(db: Session, recurring_pickup: RecurringPickup) -> RecurringPickup:
        db.add(recurring_pickup)
        db.commit()
        db.refresh(recurring_pickup)
        return recurring_pickup

    @staticmethod
    def get_by_org(db: Session, org_id: int) -> List[RecurringPickup]:
        return db.query(RecurringPickup).filter(
            RecurringPickup.organization_id == org_id,
            RecurringPickup.is_active == True
        ).all()

    @staticmethod
    def get_due_recurring_pickups(db: Session) -> List[RecurringPickup]:
        return db.query(RecurringPickup).filter(
            RecurringPickup.is_active == True,
            RecurringPickup.next_run_at <= datetime.utcnow()
        ).all()

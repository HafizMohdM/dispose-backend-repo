from sqlalchemy.orm import Session
from app.models.pickup_exception import PickupException, ExceptionType
from app.models.pickup import Pickup
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime

class PickupExceptionRepository:

    @staticmethod
    def create_exception(db: Session, pickup_id: int, exception_type: ExceptionType, 
                        notes: Optional[str], reported_by_id: int) -> PickupException:
        
        # Verify pickup exists
        pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")

        exception = PickupException(
            pickup_id=pickup_id,
            exception_type=exception_type,
            notes=notes,
            reported_by_id=reported_by_id
        )
        db.add(exception)
        db.flush()
        return exception

    @staticmethod
    def get_exceptions_by_pickup(db: Session, pickup_id: int) -> List[PickupException]:
        return db.query(PickupException).filter(
            PickupException.pickup_id == pickup_id
        ).order_by(PickupException.created_at.desc()).all()

    @staticmethod
    def get_exception_by_id(db: Session, exception_id: int) -> Optional[PickupException]:
        return db.query(PickupException).filter(PickupException.id == exception_id).first()

    @staticmethod
    def resolve_exception(db: Session, exception_id: int, resolved_by_id: int) -> PickupException:
        exception = db.query(PickupException).filter(PickupException.id == exception_id).first()
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        exception.resolved = True
        exception.resolved_at = datetime.utcnow()
        exception.resolved_by_id = resolved_by_id
        db.flush()
        return exception
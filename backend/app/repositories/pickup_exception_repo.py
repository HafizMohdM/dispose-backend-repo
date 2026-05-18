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

    @staticmethod
    def get_filtered_exceptions(
        db: Session,
        organization_id: Optional[int] = None,
        resolved: Optional[bool] = None,
        exception_type: Optional[ExceptionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PickupException]:
        query = db.query(PickupException).join(Pickup, Pickup.id == PickupException.pickup_id)
        
        if organization_id is not None:
            query = query.filter(Pickup.organization_id == organization_id)
            
        if resolved is not None:
            query = query.filter(PickupException.resolved == resolved)
            
        if exception_type is not None:
            query = query.filter(PickupException.exception_type == exception_type)
            
        if start_date is not None:
            query = query.filter(PickupException.created_at >= start_date)
            
        if end_date is not None:
            query = query.filter(PickupException.created_at <= end_date)
            
        return query.order_by(PickupException.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count_filtered_exceptions(
        db: Session,
        organization_id: Optional[int] = None,
        resolved: Optional[bool] = None,
        exception_type: Optional[ExceptionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        from sqlalchemy import func
        query = db.query(func.count(PickupException.id)).join(Pickup, Pickup.id == PickupException.pickup_id)
        
        if organization_id is not None:
            query = query.filter(Pickup.organization_id == organization_id)
            
        if resolved is not None:
            query = query.filter(PickupException.resolved == resolved)
            
        if exception_type is not None:
            query = query.filter(PickupException.exception_type == exception_type)
            
        if start_date is not None:
            query = query.filter(PickupException.created_at >= start_date)
            
        if end_date is not None:
            query = query.filter(PickupException.created_at <= end_date)
            
        return query.scalar() or 0

    @staticmethod
    def get_exceptions_stats(
        db: Session,
        organization_id: Optional[int] = None,
    ) -> dict:
        from sqlalchemy import func
        
        # Base query joined to Pickup to enforce organization context
        base_query = db.query(PickupException).join(Pickup, Pickup.id == PickupException.pickup_id)
        if organization_id is not None:
            base_query = base_query.filter(Pickup.organization_id == organization_id)
            
        total = base_query.count()
        resolved = base_query.filter(PickupException.resolved == True).count()
        unresolved = total - resolved
        
        resolution_rate = 0.0
        if total > 0:
            resolution_rate = round((resolved / total) * 100, 2)
            
        # Breakdown by ExceptionType
        breakdown_query = (
            db.query(PickupException.exception_type, func.count(PickupException.id))
            .join(Pickup, Pickup.id == PickupException.pickup_id)
        )
        if organization_id is not None:
            breakdown_query = breakdown_query.filter(Pickup.organization_id == organization_id)
            
        breakdown_results = breakdown_query.group_by(PickupException.exception_type).all()
        
        type_breakdown = {
            t.value if hasattr(t, "value") else str(t): count 
            for t, count in breakdown_results
        }
        
        return {
            "total_exceptions": total,
            "resolved_count": resolved,
            "unresolved_count": unresolved,
            "resolution_rate": resolution_rate,
            "type_breakdown": type_breakdown
        }
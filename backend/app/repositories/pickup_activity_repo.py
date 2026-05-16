from sqlalchemy.orm import Session
from app.models.pickup_activity import PickupActivity, ActivityType
from typing import Dict, Any

class PickupActivityRepository:
    
    @staticmethod
    def log_activity(
        db: Session, 
        pickup_id: int, 
        user_id: int, 
        activity_type: ActivityType, 
        description: str, 
        notes: str = None, 
        metadata_payload: Dict[str, Any] = None
    ) -> PickupActivity:
        activity = PickupActivity(
            pickup_id=pickup_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            notes=notes,
            metadata_payload=metadata_payload or {}
        )
        db.add(activity)
        db.flush()
        return activity

    @staticmethod
    def get_timeline(db: Session, pickup_id: int) -> list[PickupActivity]:
        return db.query(PickupActivity)\
            .filter(PickupActivity.pickup_id == pickup_id)\
            .order_by(PickupActivity.created_at.desc())\
            .all()
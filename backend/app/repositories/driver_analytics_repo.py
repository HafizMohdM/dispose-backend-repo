from sqlalchemy.orm import Session
from sqlalchemy import select, func , desc
from typing import List


from app.models.driver import Driver
from app.models.pickup import Pickup
from app.models.pickup_assignment import PickupAssignment


class DriverAnalyticsRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_driver_stats(
        self, 
        organization_id: int,
        limit: int = 10,
        ):

        stmt = (
            select(
                Driver.id,
                Driver.name,
                Driver.phone,
                func.count(Pickup.id).label("completed_pickups")
            )
            .join(PickupAssignment, PickupAssignment.driver_id == Driver.id)
            .join(Pickup, Pickup.id == PickupAssignment.pickup_id)
            .where(
                Driver.organization_id == organization_id,
                Pickup.status == "COMPLETED",
            )
            .group_by(Driver.id)
            .order_by(desc("completed_pickups"))
            .limit(limit)
        )
        return self.db.execute(stmt).all()


    def get_driver_performance(
        self,
        organization_id: int,
        driver_id,
        ):

        stmt = (
            select(
                Driver.id,
                Driver.name,
                func.count(PickupAssignment.id).label("total_assignments"),
                func.count(
                    func.nullif(Pickup.status != "COMPLETED", True)
                ).label("completed_pickups"),
                func.count(
                    func.nullif(Pickup.status != "CANCELLED", True)
                ).label("cancelled_pickups"),
            )
            .join(PickupAssignment, PickupAssignment.driver_id == Driver.id)
            .join(Pickup, Pickup.id == PickupAssignment.pickup_id)
            .where(
                Driver.organization_id == organization_id,
                Driver.id == driver_id
            )
            .group_by(Driver.id)
        )

        return self.db.execute(stmt).first()

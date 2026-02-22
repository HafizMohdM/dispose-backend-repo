from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.driver import Driver, DriverLocation, DriverAvailability
from app.utils.enums import DriverStatus, DriverAvailabilityStatus


class DriverRepository:

    def __init__(self, db: Session):
        self.db = db

    
    def get_driver_by_id(
        self,
        driver_id: UUID,
        organization_id: UUID,
    ) -> Optional[Driver]:

        stmt = select(Driver).where(
            Driver.id == driver_id,
            Driver.organization_id == organization_id,
            Driver.status != DriverStatus.DELETED,
        )
        return self.db.scalar(stmt)

    def get_driver_by_mobile(
        self,
        mobile: str,
        organization_id: UUID,
    ) -> Optional[Driver]:

        stmt = select(Driver).where(
            Driver.mobile == mobile,
            Driver.organization_id == organization_id,
            Driver.status != DriverStatus.DELETED,
        )
        return self.db.scalar(stmt)

    def list_drivers_by_organization(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Driver]:

        stmt = (
            select(Driver)
            .where(
                Driver.organization_id == organization_id,
                Driver.status != DriverStatus.DELETED,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create_driver(self, driver: Driver) -> Driver:
        self.db.add(driver)
        self.db.flush()
        return driver

    def update_driver(
        self,
        driver: Driver,
        update_data: dict,
        updated_by: UUID,
    ) -> Driver:

        for field, value in update_data.items():
            setattr(driver, field, value)

        driver.updated_by = updated_by
        self.db.flush()
        return driver

    def soft_delete_driver(
        self,
        driver: Driver,
        updated_by: UUID,
    ) -> Driver:

        driver.status = DriverStatus.DELETED
        driver.updated_by = updated_by
        self.db.flush()
        return driver

   

    def set_driver_status(
        self,
        driver: Driver,
        status: DriverStatus,
        updated_by: UUID,
    ) -> Driver:

        driver.status = status
        driver.updated_by = updated_by
        self.db.flush()
        return driver

    def get_drivers_by_status(
        self,
        organization_id: UUID,
        status: DriverStatus,
    ) -> List[Driver]:

        stmt = (
            select(Driver)
            .where(
                Driver.organization_id == organization_id,
                Driver.status == status,
            )
        )
        return list(self.db.scalars(stmt).all())

    def get_available_drivers(
        self,
        organization_id: UUID,
        limit: int = 50,
    ) -> List[Driver]:

        stmt = (
            select(Driver)
            .join(
                DriverAvailability,
                DriverAvailability.driver_id == Driver.id,
            )
            .where(
                Driver.organization_id == organization_id,
                Driver.status == DriverStatus.ACTIVE,
                DriverAvailability.status == DriverAvailabilityStatus.AVAILABLE,
                DriverAvailability.is_on_duty == True,
            )
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_driver_availability(
        self,
        driver_id: UUID,
    ) -> Optional[DriverAvailability]:

        stmt = select(DriverAvailability).where(
            DriverAvailability.driver_id == driver_id,
        )
        return self.db.scalar(stmt)

    def set_driver_availability(
        self,
        driver_id: UUID,
        status: DriverAvailabilityStatus,
        is_on_duty: bool,
    ) -> DriverAvailability:

        availability = self.get_driver_availability(driver_id)

        if availability:
            availability.status = status
            availability.is_on_duty = is_on_duty
        else:
            availability = DriverAvailability(
                driver_id=driver_id,
                status=status,
                is_on_duty=is_on_duty,
            )
            self.db.add(availability)

        self.db.flush()
        return availability

    

    def create_driver_location(
        self,
        location: DriverLocation,
    ) -> DriverLocation:

        self.db.add(location)
        self.db.flush()
        return location

    def get_latest_driver_location(
        self,
        driver_id: UUID,
    ) -> Optional[DriverLocation]:

        stmt = (
            select(DriverLocation)
            .where(DriverLocation.driver_id == driver_id)
            .order_by(DriverLocation.recorded_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    

    def get_drivers_by_ids(
        self,
        organization_id: UUID,
        driver_ids: List[UUID],
    ) -> List[Driver]:

        stmt = (
            select(Driver)
            .where(
                Driver.organization_id == organization_id,
                Driver.id.in_(driver_ids),
                Driver.status != DriverStatus.DELETED,
            )
        )
        return list(self.db.scalars(stmt).all())

    def driver_exists(
        self,
        driver_id: UUID,
        organization_id: UUID,
    ) -> bool:

        stmt = select(Driver.id).where(
            Driver.id == driver_id,
            Driver.organization_id == organization_id,
        )
        return self.db.scalar(stmt) is not None
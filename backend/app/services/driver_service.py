from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.driver import Driver, DriverLocation
from app.repositories.driver_repo import DriverRepository
from app.utils.enums import DriverStatus, DriverAvailabilityStatus
from app.services.audit_service import log_event


class DriverService:
    def __init__(self, db: Session):
        self.db = db
        self.driver_repo = DriverRepository(db)


    def create_driver(
        self,
        organization_id: UUID,
        name: str,
        mobile: str,
        email: Optional[str],
        license_number: Optional[str],
        license_expiry,
        created_by: UUID,
    ) -> Driver:
        
        "prevent duplicate mobile inside same organization "
        existing = self.driver_repo.get_driver_by_mobile(
            mobile =mobile,
            organization_id=organization_id,
        )
        if existing:
            raise ValueError("Driver with this mobile already exists")

        driver = Driver(
            organization_id=organization_id,
            name=name,
            mobile=mobile,
            email=email,
            license_number=license_number,
            license_expiry=license_expiry,
            created_by=created_by,
            status=DriverStatus.ACTIVE,
        )
        driver = self.driver_repo.create_driver(driver)

        log_event(
            db=self.db,
            user_id=created_by,
            action="driver_created",
            org_id=organization_id,
            metadata={"driver_id": str(driver.id)},
        )
        return driver

    def get_driver(
        self,
        driver_id: UUID,
        organization_id: UUID,
    ) -> Optional[Driver]:

        return self.driver_repo.get_driver_by_id(
            driver_id=driver_id,
            organization_id=organization_id,
        )

    def list_drivers(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Driver]:

        return self.driver_repo.list_drivers_by_organization(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
        )

    def update_driver(
        self,
        driver_id: UUID,
        organization_id: UUID,
        update_data: dict,
        updated_by: UUID,
    ) -> Driver:

        driver = self.driver_repo.get_driver_by_id(
            driver_id,
            organization_id,
        )

        if not driver:
            raise ValueError("Driver not found")

        driver = self.driver_repo.update_driver(
            driver,
            update_data,
            updated_by,
        )

        log_event(
            db=self.db,
            user_id=updated_by,
            action="driver_updated",
            org_id=organization_id,
            metadata={"driver_id": str(driver.id)},
        )

        return driver
        
    def soft_delete_driver(
        self,
        driver_id: UUID,
        organization_id: UUID,
        deleted_by: UUID,
    ) -> Driver:

        driver = self.driver_repo.get_driver_by_id(
            driver_id,
            organization_id,
        )

        if not driver:
            raise ValueError("Driver not found")

        driver = self.driver_repo.soft_delete_driver(
            driver,
            deleted_by,
        )

        log_event(
            db=self.db,
            user_id=deleted_by,
            action="driver_deleted",
            org_id=organization_id,
            metadata={"driver_id": str(driver.id)},
        )

        return driver

    def set_driver_availability(
        self,
        driver_id: UUID,
        organization_id: UUID,
        status: DriverAvailabilityStatus,
        is_on_duty: bool,
        updated_by: UUID,
    ):

        driver = self.driver_repo.get_driver_by_id(
            driver_id,
            organization_id,
        )

        if not driver:
            raise ValueError("Driver not found")

        availability = self.driver_repo.set_driver_availability(
            driver_id=driver_id,
            status=status,
            is_on_duty=is_on_duty,
        )

        log_event(
            db=self.db,
            user_id=updated_by,
            action="driver_availability_updated",
            org_id=organization_id,
            metadata={
                "driver_id": str(driver_id),
                "status": status.value,
            },
        )

        return availability

    def update_driver_location(
        self,
        driver_id: UUID,
        organization_id: UUID,
        latitude: float,
        longitude: float,
        accuracy: Optional[float],
    ) -> DriverLocation:

        driver = self.driver_repo.get_driver_by_id(
            driver_id,
            organization_id,
        )

        if not driver:
            raise ValueError("Driver not found")

        location = DriverLocation(
            driver_id=driver_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )

        return self.driver_repo.create_driver_location(location)


    def get_available_drivers(
        self,
        organization_id: UUID,
        limit: int = 50,
    ):
        return self.driver_repo.get_available_drivers(
            organization_id=organization_id,
            limit=limit,
        )

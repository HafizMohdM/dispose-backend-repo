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
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ):
        return self.driver_repo.get_available_drivers(
            organization_id=organization_id,
            limit=limit,
            lat=lat,
            lng=lng
        )

    # --- Phase 2: GPS Polling Backups ---
    
    def process_heartbeat(self, driver_id: UUID, organization_id: int, latitude: float, longitude: float):
        # Update driver location as heartbeat
        self.update_driver_location(driver_id, organization_id, latitude, longitude, accuracy=None)
        return {"status": "heartbeat_recorded", "driver_id": driver_id}

    def get_live_map(self, organization_id: int):
        # Returns latest known location for all active drivers in the org
        # In a real system, you might fetch from Redis or from the `driver_locations` table using a groupwise max query.
        # Simple fallback implementation using Driver Availability
        from app.models.driver import DriverLocation, Driver
        latest_locations = self.db.query(DriverLocation, Driver).join(Driver).filter(
            Driver.organization_id == organization_id,
            Driver.status == DriverStatus.ACTIVE
        ).order_by(DriverLocation.recorded_at.desc()).all()
        
        # Deduplicate to get only latest per driver
        seen = set()
        results = []
        for loc, drv in latest_locations:
            if drv.id not in seen:
                seen.add(drv.id)
                results.append({
                    "driver_id": drv.id,
                    "driver_name": drv.name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "recorded_at": loc.recorded_at
                })
        return results

    def get_live_status(self, organization_id: int):
        from app.models.driver import DriverAvailability, Driver
        statuses = self.db.query(DriverAvailability, Driver).join(Driver).filter(
            Driver.organization_id == organization_id
        ).all()
        return [
            {
                "driver_id": drv.id,
                "driver_name": drv.name,
                "status": avail.status,
                "is_on_duty": avail.is_on_duty,
                "updated_at": avail.updated_at
            }
            for avail, drv in statuses
        ]

    # --- Phase 4: Shift Management ---
    
    def clock_in(self, driver_id: UUID, organization_id: int):
        from app.models.driver_operations import DriverShift, ShiftStatus
        from app.models.driver import DriverAvailability
        
        # Check if already clocked in
        active_shift = self.db.query(DriverShift).filter(
            DriverShift.driver_id == driver_id,
            DriverShift.status == ShiftStatus.ACTIVE
        ).first()
        
        if active_shift:
            raise ValueError("Driver is already clocked in.")
            
        new_shift = DriverShift(
            driver_id=driver_id,
            organization_id=organization_id,
            status=ShiftStatus.ACTIVE
        )
        self.db.add(new_shift)
        
        # Cascading state change
        avail = self.db.query(DriverAvailability).filter(DriverAvailability.driver_id == driver_id).first()
        if avail:
            avail.is_on_duty = True
        else:
            avail = DriverAvailability(driver_id=driver_id, is_on_duty=True)
            self.db.add(avail)
            
        self.db.commit()
        self.db.refresh(new_shift)
        return new_shift

    def clock_out(self, driver_id: UUID, organization_id: int):
        from app.models.driver_operations import DriverShift, ShiftStatus
        from app.models.driver import DriverAvailability
        from datetime import datetime
        
        active_shift = self.db.query(DriverShift).filter(
            DriverShift.driver_id == driver_id,
            DriverShift.status == ShiftStatus.ACTIVE
        ).first()
        
        if not active_shift:
            raise ValueError("No active shift found for this driver.")
            
        active_shift.status = ShiftStatus.COMPLETED
        active_shift.clock_out_time = datetime.utcnow()
        
        # Cascading state change
        avail = self.db.query(DriverAvailability).filter(DriverAvailability.driver_id == driver_id).first()
        if avail:
            avail.is_on_duty = False
            
        self.db.commit()
        self.db.refresh(active_shift)
        return active_shift

    def get_shifts(self, organization_id: int, skip: int = 0, limit: int = 50):
        from app.models.driver_operations import DriverShift
        return self.db.query(DriverShift).filter(
            DriverShift.organization_id == organization_id
        ).offset(skip).limit(limit).all()

    # --- Phase 4: Driver Compliance ---
    
    def upload_document(self, driver_id: UUID, organization_id: int, document_type: str, file_url: str):
        from app.models.driver_operations import DriverDocument, DocumentVerificationStatus
        
        doc = DriverDocument(
            driver_id=driver_id,
            organization_id=organization_id,
            document_type=document_type,
            file_url=file_url,
            verification_status=DocumentVerificationStatus.PENDING
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_documents(self, driver_id: UUID, organization_id: int):
        from app.models.driver_operations import DriverDocument
        return self.db.query(DriverDocument).filter(
            DriverDocument.driver_id == driver_id,
            DriverDocument.organization_id == organization_id
        ).all()

    def verify_document(self, document_id: UUID, organization_id: int, status: str, rejection_reason: Optional[str], updated_by: int):
        from app.models.driver_operations import DriverDocument, DocumentVerificationStatus
        from datetime import datetime
        
        doc = self.db.query(DriverDocument).filter(
            DriverDocument.id == document_id,
            DriverDocument.organization_id == organization_id
        ).first()
        
        if not doc:
            raise ValueError("Document not found.")
            
        doc.verification_status = status
        doc.rejection_reason = rejection_reason if status == DocumentVerificationStatus.REJECTED else None
        doc.verified_by = updated_by
        doc.verified_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(doc)
        return doc

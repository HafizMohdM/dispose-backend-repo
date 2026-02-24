from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission

from app.services.driver_service import DriverService

from app.utils.enums import DriverStatus

from app.api.v1.drivers.driver_schemas import (
    DriverCreateRequest,
    DriverUpdateRequest,
    DriverResponse,
    DriverAvailabilityUpdateRequest,
    DriverLocationUpdateRequest,
)


router = APIRouter()

def get_org_id(current_user, request_org_id: Optional[UUID] = None) -> UUID:
    org_id = request_org_id or getattr(current_user, "current_org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required. Admins must provide it in the request."
        )
    return org_id




@router.get(
    "/available",
    response_model=List[DriverResponse],
)
def get_available_drivers(
    limit: int = 50,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:view")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    drivers = service.get_available_drivers(
        organization_id=org_id,
        limit=limit,
    )

    return drivers


@router.post(
    "",
    response_model=DriverResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_driver(
    request: DriverCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:create")),
):

    org_id = get_org_id(current_user, request.organization_id)
    service = DriverService(db)

    try:
        driver = service.create_driver(
            organization_id=org_id,
            name=request.name,
            mobile=request.mobile,
            email=request.email,
            license_number=request.license_number,
            license_expiry=request.license_expiry,
            created_by=current_user.id,
        )

        db.commit()
        return driver

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=List[DriverResponse],
)
def list_drivers(
    skip: int = 0,
    limit: int = 50,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:view")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    drivers = service.list_drivers(
        organization_id=org_id,
        skip=skip,
        limit=limit,
    )

    return drivers


@router.get(
    "/{driver_id}",
    response_model=DriverResponse,
)
def get_driver(
    driver_id: UUID,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:view")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    driver = service.get_driver(
        driver_id=driver_id,
        organization_id=org_id,
    )

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    return driver


@router.patch(
    "/{driver_id}",
    response_model=DriverResponse,
)
def update_driver(
    driver_id: UUID,
    request: DriverUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:update")),
):

    org_id = get_org_id(current_user, request.organization_id)
    service = DriverService(db)

    try:
        driver = service.update_driver(
            driver_id=driver_id,
            organization_id=org_id,
            update_data=request.dict(exclude_unset=True),
            updated_by=current_user.id,
        )

        db.commit()
        return driver

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{driver_id}",
    response_model=DriverResponse,
)
def delete_driver(
    driver_id: UUID,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:delete")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    try:
        driver = service.soft_delete_driver(
            driver_id=driver_id,
            organization_id=org_id,
            deleted_by=current_user.id,
        )

        db.commit()
        return driver

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{driver_id}/availability",
)
def update_driver_availability(
    driver_id: UUID,
    request: DriverAvailabilityUpdateRequest,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:update")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    try:
        availability = service.set_driver_availability(
            driver_id=driver_id,
            organization_id=org_id,
            status=request.status,
            is_on_duty=request.is_on_duty,
            updated_by=current_user.id,
        )

        db.commit()
        return availability

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/{driver_id}/location",
)
def update_driver_location(
    driver_id: UUID,
    request: DriverLocationUpdateRequest,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:update")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    try:
        location = service.update_driver_location(
            driver_id=driver_id,
            organization_id=org_id,
            latitude=request.latitude,
            longitude=request.longitude,
            accuracy=request.accuracy,
        )

        db.commit()
        return location

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{driver_id}/location",
)
def get_driver_latest_location(
    driver_id: UUID,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:view")),
):

    org_id = get_org_id(current_user, organization_id)
    from app.repositories.driver_repo import DriverRepository

    repo = DriverRepository(db)

    driver = repo.get_driver_by_id(
        driver_id=driver_id,
        organization_id=org_id,
    )

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    location = repo.get_latest_driver_location(driver_id)

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    return location


@router.patch(
    "/{driver_id}/activate",
    response_model=DriverResponse,
)
def activate_driver(
    driver_id: UUID,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:update")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    try:
        driver = service.update_driver(
            driver_id=driver_id,
            organization_id=org_id,
            update_data={"status": DriverStatus.ACTIVE},
            updated_by=current_user.id,
        )

        db.commit()
        return driver

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{driver_id}/deactivate",
    response_model=DriverResponse,
)
def deactivate_driver(
    driver_id: UUID,
    organization_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_permission("driver:update")),
):

    org_id = get_org_id(current_user, organization_id)
    service = DriverService(db)

    try:
        driver = service.update_driver(
            driver_id=driver_id,
            organization_id=org_id,
            update_data={"status": DriverStatus.INACTIVE},
            updated_by=current_user.id,
        )

        db.commit()
        return driver

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
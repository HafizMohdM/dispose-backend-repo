from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_organization
from app.core.permissions import require_permission

from app.services.system_setting_service import SystemSettingService
from app.api.v1.system.system_setting_schemas import (
    SystemSettingResponse,
    SystemSettingUpdateRequest,
)

router = APIRouter()


@router.get(
    "",
    response_model=list[SystemSettingResponse],
)
def get_settings(
    db: Session = Depends(get_db),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("system_settings:view")),
):

    service = SystemSettingService(db)

    return service.get_settings(org.id)


@router.patch(
    "",
    response_model=SystemSettingResponse,
)
def update_setting(
    request: SystemSettingUpdateRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("system_settings:update")),
):

    service = SystemSettingService(db)

    setting = service.set_setting(
        key=request.key,
        value=request.value,
        organization_id=org.id,
    )

    db.commit()

    return setting
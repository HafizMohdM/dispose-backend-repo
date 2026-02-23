from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user,get_current_organization
from app.core.permissions import require_permission


from app.repositories.audit_repo import AuditRepository

from app.api.v1.audit.audit_schemas import AuditLogResponse

router = APIRouter()


@router.get(
    "",
    response_model=List[AuditLogResponse]
)

def list_audit_logs(
    skip:int = 0,
    limit:int =50,
    db:Session = Depends(get_db),
    organization = Depends(get_current_organization),
    _: bool = Depends(require_permission("audit:view")),
):

    repo = AuditRepository(db)

    logs = repo.list_audit_logs(
        organization_id = organization.id,
        skip=skip,
        limit=limit,
    )

    return logs


@router.get(
    "/{audit_log_id}",
    response_model=AuditLogResponse,
)
def get_audit_log(
    audit_log_id: int,
    db: Session = Depends(get_db),
    organization = Depends(get_current_organization),
    _: bool = Depends(require_permission("audit:view")),
):
    repo= AuditRepository(db)

    log = repo.get_audit_log_by_id(
        audit_log_id = audit_log_id,
        organization_id = organization.id,
    )

    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return log


@router.get(
    "/user/{user_id}",
    response_model=List[AuditLogResponse],
)

def get_user_audit_logs(
    user_id: int,
    skip: int =0,
    limit:int=50,
    db:Session = Depends(get_db),
    organization = Depends(get_current_organization),
    _: bool = Depends(require_permission("audit:view")),
):
    repo = AuditRepository(db)

    logs = repo.get_user_audit_logs(
        organization_id = organization.id,
        user_id = user_id,
        skip=skip,
        limit=limit,
    )

    return logs


@router.get(
    "/entity/{entity_type}",
    response_model=List[AuditLogResponse],
)
def get_entity_audit_logs(
    entity_type: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("audit:view")),
):

    repo = AuditRepository(db)

    logs = repo.get_entity_audit_logs(
        organization_id=organization.id,
        entity_type=entity_type,
        skip=skip,
        limit=limit,
    )

    return logs


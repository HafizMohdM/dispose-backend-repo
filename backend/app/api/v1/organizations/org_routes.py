from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.organization_service import OrganizationService
from app.api.v1.organizations.org_schemas import OrganizationCreate, OrganizationResponse
from app.core.permissions import require_permission
from app.api.v1.organizations.org_schemas import OrganizationUpdate


router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_permission("organization.create"))]
)
def create_organization(data: OrganizationCreate, db: Session = Depends(get_db)):
    return OrganizationService.create_organization(db, data)


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_permission("organization.view"))]
)
def get_organization(org_id: int, db: Session = Depends(get_db)):
    return OrganizationService.get_organization(db, org_id)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    dependencies=[Depends(require_permission("organization.view"))]
)
def list_organizations(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    return OrganizationService.list_organizations(db, page, limit)


@router.put(
    "/{org_id}/approve",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_permission("organization.approve"))]
)
def approve_organization(org_id: int, db: Session = Depends(get_db)):
    return OrganizationService.approve_organization(db, org_id)

@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(require_permission("organization.update"))]
)
def update_organization(org_id: int, data: OrganizationUpdate, db: Session = Depends(get_db)):
    return OrganizationService.update_organization(db, org_id, data)
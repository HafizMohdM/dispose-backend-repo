from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.organizations.member_schemas import MemberCreate, MemberUpdate, MemberResponse
from app.services.organization_member_service import OrganizationMemberService
from typing import List

router = APIRouter()

@router.get(
    "",
    response_model=List[MemberResponse],
    dependencies=[Depends(require_permission("membership.view"))]
)
def list_members(org_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return OrganizationMemberService.list_members(db, org_id, current_user)

@router.post(
    "",
    response_model=MemberResponse,
    dependencies=[Depends(require_permission("membership.create"))]
)
def add_member(org_id: int, data: MemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return OrganizationMemberService.add_member(db, org_id, data, current_user)

@router.patch(
    "/{user_id}",
    response_model=MemberResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(require_permission("membership.update"))]
)
def update_member_role(org_id: int, user_id: int, data: MemberUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return OrganizationMemberService.update_member(db, org_id, user_id, data, current_user)

@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_permission("membership.delete"))]
)
def remove_member(org_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return OrganizationMemberService.remove_member(db, org_id, user_id, current_user)

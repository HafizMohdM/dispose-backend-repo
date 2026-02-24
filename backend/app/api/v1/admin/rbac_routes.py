from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.api.v1.admin.rbac_schemas import (
    RoleResponseSchema, 
    RoleCreateSchema, 
    RoleUpdateSchema, 
    PermissionResponseSchema, 
    PermissionAssignSchema
)
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/roles", tags=["Admin Roles & Permissions"])

@router.get("/", response_model=List[RoleResponseSchema])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage"))
):
    """List all roles and their assigned permissions."""
    return RBACService.get_all_roles(db)


@router.post("/", response_model=RoleResponseSchema, status_code=status.HTTP_201_CREATED)
def create_role(
    request: RoleCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage"))
):
    """Create a new custom role."""
    return RBACService.create_role(db, request, current_user)


@router.patch("/{role_id}", response_model=RoleResponseSchema)
def update_role(
    role_id: int,
    request: RoleUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage"))
):
    """
    Update a role's description.
    System roles cannot be renamed. Custom roles can technically be renamed in DB,
    but this endpoint intentionally only allows modifying descriptions for safety.
    """
    return RBACService.update_role(db, role_id, request, current_user)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage"))
):
    """
    Delete a role. 
    Cannot delete system roles or roles assigned to existing users.
    """
    RBACService.delete_role(db, role_id, current_user)


@router.get("/permissions", response_model=List[PermissionResponseSchema])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage"))
):
    """List all available permissions in the system."""
    return RBACService.get_all_permissions(db)


@router.patch("/{role_id}/permissions", response_model=RoleResponseSchema)
def assign_permissions(
    role_id: int,
    request: PermissionAssignSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage"))
):
    """
    Atomically reassign permissions to a role.
    Prevents ADMIN lockouts and critical system failures.
    """
    return RBACService.assign_role_permissions(db, role_id, request, current_user)

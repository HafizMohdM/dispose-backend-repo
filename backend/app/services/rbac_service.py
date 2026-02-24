from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.models.user import User
from app.api.v1.admin.rbac_schemas import RoleCreateSchema, RoleUpdateSchema, PermissionAssignSchema, RoleResponseSchema, PermissionResponseSchema
from app.repositories.rbac_repo import RBACRepository
from app.models.audit_log import AuditLog
import json
from datetime import datetime

class RBACService:
    
    # Critical permissions that can never be removed from the ADMIN role
    CRITICAL_PERMISSIONS = {
        "rbac.manage",
        "subscription.manage",
        "pickup.manage",
        "organization.approve"
    }

    @staticmethod
    def get_all_roles(db: Session) -> List[RoleResponseSchema]:
        roles = RBACRepository.get_all_roles(db)
        return [
            RoleResponseSchema(
                id=r.id,
                name=r.name,
                description=r.description,
                is_system_role=r.is_system_role,
                permissions=[rp.permission.code for rp in r.permissions]
            ) for r in roles
        ]

    @staticmethod
    def create_role(db: Session, request: RoleCreateSchema, current_user: User) -> RoleResponseSchema:
        existing_role = RBACRepository.get_role_by_name(db, request.name.upper())
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with name '{request.name.upper()}' already exists"
            )

        new_role = RBACRepository.create_role(db, request.name, request.description)
        
        audit_log = AuditLog(
            entity_type="role",
            entity_id=new_role.id,
            action="CREATE_ROLE",
            old_value=None,
            new_value=json.dumps({"name": new_role.name, "description": new_role.description}),
            changed_by=current_user.id,
            created_at=datetime.utcnow()
        )
        db.add(audit_log)

        db.commit()
        db.refresh(new_role)
        
        return RoleResponseSchema(
            id=new_role.id,
            name=new_role.name,
            description=new_role.description,
            is_system_role=new_role.is_system_role,
            permissions=[]
        )

    @staticmethod
    def update_role(db: Session, role_id: int, request: RoleUpdateSchema, current_user: User) -> RoleResponseSchema:
        role = RBACRepository.get_role_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        # System Role Name Protection
        if role.is_system_role and request.name and request.name.upper() != role.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System roles cannot be renamed. Only descriptions can be updated."
            )

        old_description = role.description
        old_name = role.name

        # If it's not a system role, allow name changes if provided
        new_name = role.name
        if not role.is_system_role and request.name:
            new_name = request.name.upper()
            # check duplicate name
            if new_name != old_name:
                collision = RBACRepository.get_role_by_name(db, new_name)
                if collision:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name already in use.")
            role.name = new_name

        updated_role = RBACRepository.update_role_description(db, role, request.description if request.description is not None else role.description)
        
        audit_log = AuditLog(
            entity_type="role",
            entity_id=role.id,
            action="UPDATE_ROLE",
            old_value=json.dumps({"name": old_name, "description": old_description}),
            new_value=json.dumps({"name": new_name, "description": updated_role.description}),
            changed_by=current_user.id,
            created_at=datetime.utcnow()
        )
        db.add(audit_log)
        
        db.commit()
        db.refresh(updated_role)
        
        # We need to reshape the response here
        updated_role_obj = RBACRepository.get_role_by_id(db, updated_role.id)
        return RoleResponseSchema(
            id=updated_role_obj.id,
            name=updated_role_obj.name,
            description=updated_role_obj.description,
            is_system_role=updated_role_obj.is_system_role,
            permissions=[rp.permission.code for rp in updated_role_obj.permissions]
        )

    @staticmethod
    def delete_role(db: Session, role_id: int, current_user: User):
        role = RBACRepository.get_role_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="System roles cannot be deleted"
            )

        if RBACRepository.is_role_assigned_to_users(db, role_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is assigned to users and cannot be deleted"
            )

        RBACRepository.delete_role(db, role)
        
        audit_log = AuditLog(
            entity_type="role",
            entity_id=role_id,
            action="DELETE_ROLE",
            old_value=json.dumps({"name": role.name, "is_active": True}),
            new_value=json.dumps({"is_active": False}),
            changed_by=current_user.id,
            created_at=datetime.utcnow()
        )
        db.add(audit_log)
        
        db.commit()

    @staticmethod
    def get_all_permissions(db: Session) -> List[PermissionResponseSchema]:
        permissions = RBACRepository.get_all_permissions(db)
        return [PermissionResponseSchema.model_validate(p) for p in permissions]

    @staticmethod
    def assign_role_permissions(db: Session, role_id: int, request: PermissionAssignSchema, current_user: User) -> RoleResponseSchema:
        role = RBACRepository.get_role_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        # 1. Validate all requested permissions actually exist
        requested_permissions = RBACRepository.get_permissions_by_ids(db, request.permission_ids)
        if len(requested_permissions) != len(request.permission_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="One or more provided permission IDs are invalid"
            )
        
        requested_permission_codes = {p.code for p in requested_permissions}

        # 2. Critical system role logic
        if role.is_system_role and role.name == "ADMIN":
            if not request.permission_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove all permissions from ADMIN role")
            
            for critical_perm in RBACService.CRITICAL_PERMISSIONS:
                if critical_perm not in requested_permission_codes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove critical permissions from ADMIN role"
                    )

        # 3. Prevent Self-Lockout (Admin removing their own rbac.manage access)
        # Check if the current user belongs to the role they are editing
        is_modifying_own_role = False
        for current_role in current_user.roles:
            if current_role.role_id == role.id:
                is_modifying_own_role = True
                break
                
        if is_modifying_own_role and "rbac.manage" not in requested_permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Self-lockout prevented: You cannot remove your own administrative access."
            )

        # 4. Perform atomic update
        old_permissions = [rp.permission.code for rp in role.permissions]
        
        try:
            RBACRepository.assign_role_permissions(db, role_id, request.permission_ids)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign permissions")

        audit_log = AuditLog(
            entity_type="role_permissions",
            entity_id=role.id,
            action="PERMISSION_UPDATE",
            old_value=json.dumps(old_permissions),
            new_value=json.dumps(list(requested_permission_codes)),
            changed_by=current_user.id,
            created_at=datetime.utcnow()
        )
        db.add(audit_log)

        db.commit()
        
        # Refetch to get the latest join for the response
        updated_role_obj = RBACRepository.get_role_by_id(db, role.id)
        return RoleResponseSchema(
            id=updated_role_obj.id,
            name=updated_role_obj.name,
            description=updated_role_obj.description,
            is_system_role=updated_role_obj.is_system_role,
            permissions=[rp.permission.code for rp in updated_role_obj.permissions]
        )

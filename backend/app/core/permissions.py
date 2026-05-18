from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.role_mapping import UserRole, RolePermission
from app.models.role import Role, Permission


def check_permission_inheritance(required_permission: str, user_permissions: list[str]) -> bool:
    """
    Evaluates wildcard inheritance (e.g. 'admin.*' covers 'admin.view').
    Also checks exact matches.
    """
    if required_permission in user_permissions:
        return True
        
    for perm in user_permissions:
        if perm.endswith('.*'):
            base_perm = perm[:-2]
            if required_permission.startswith(base_perm):
                return True
    return False


def require_permission(permission_name: str):
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        # Enforce scoping to the user's actively selected tenant with intelligent self-healing fallback
        active_org_id = getattr(current_user, "current_org_id", getattr(current_user, "organization_id", None))
        
        if not active_org_id:
            # Fallback to user's first associated organization to prevent hard 400 blocks for un-scoped tokens
            user_role = db.query(UserRole).filter(UserRole.user_id == current_user.id).first()
            if user_role:
                active_org_id = user_role.org_id
                current_user.current_org_id = active_org_id

        if not active_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization context required for scoped authorization."
            )

        permissions = (
            db.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == current_user.id,
                UserRole.org_id == active_org_id  # <--- Scoped Context Enforcement
            )
            .all()
        )
        permission_names = [p.code for p in permissions]

        if not check_permission_inheritance(permission_name, permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Requires '{permission_name}'",
            )

        return current_user
    return permission_checker


def require_feature_flag(flag_key: str):
    """
    Dynamic Feature Flag Dependency using the SystemSetting table.
    Ensures a specific route is accessible only if the feature is toggled on.
    """
    def feature_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        from app.models.system_setting import SystemSetting
        active_org_id = getattr(current_user, "current_org_id", getattr(current_user, "organization_id", None))
        
        if not active_org_id:
            user_role = db.query(UserRole).filter(UserRole.user_id == current_user.id).first()
            if user_role:
                active_org_id = user_role.org_id
                current_user.current_org_id = active_org_id
                
        # Check org-specific override first, then fallback to global
        setting = db.query(SystemSetting).filter(
            SystemSetting.key == flag_key,
            (SystemSetting.organization_id == active_org_id) | (SystemSetting.is_global == True)
        ).order_by(SystemSetting.organization_id.desc()).first()
        
        if not setting or setting.value.lower() != 'true':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{flag_key}' is not enabled for this organization."
            )
        return current_user
    return feature_checker
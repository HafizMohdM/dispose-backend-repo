from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.permissions import require_permission
from app.core.dependencies import get_db
from app.models.user import User
from app.models.role import Role
from app.models.role_mapping import UserRole
from app.services.audit_service import log_event

router = APIRouter()


@router.get("/test-admin")
def test_admin_access(
    current_user: User = Depends(require_permission("admin.access"))
):
    return {
        "message": "Admin access granted",
        "user_id": current_user.id,
        "mobile": current_user.mobile,
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.access")),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    """
    List all users with pagination and optional active filter
    """

    query = db.query(User)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "mobile": u.mobile,
                "email": u.email,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.access")),
):
    """
    Get a single user's details including their roles
    """

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    roles = (
        db.query(
            Role.name.label("role"),
            UserRole.org_id.label("org_id"),
            UserRole.created_at.label("assigned_at"),
        )
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )

    return {
        "user": {
            "id": user.id,
            "mobile": user.mobile,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
        "roles": [
            {
                "role": r.role,
                "org_id": r.org_id,
                "assigned_at": r.assigned_at,
            }
            for r in roles
        ],
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role_name: str,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.access")),
):
    """
    Update a user's role for a specific organization
    """

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_name}' not found",
        )

    user_role = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_id,
            UserRole.org_id == org_id,
        )
        .first()
    )

    if user_role:
        user_role.role_id = role.id
    else:
        from datetime import datetime

        user_role = UserRole(
            user_id=user_id,
            role_id=role.id,
            org_id=org_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user_role)

    db.commit()

    log_event(
        db,
        current_user.id,
        "ADMIN_ROLE_UPDATED",
        org_id=org_id,
        metadata={"target_user_id": user_id, "new_role": role_name},
    )

    return {
        "message": "User role updated successfully",
        "user_id": user_id,
        "role": role_name,
        "org_id": org_id,
    }


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.access")),
):
    """
    Activate or deactivate a user account
    """

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own account status",
        )

    user.is_active = is_active
    db.commit()

    action = "ADMIN_USER_ACTIVATED" if is_active else "ADMIN_USER_DEACTIVATED"
    log_event(
        db,
        current_user.id,
        action,
        metadata={"target_user_id": user_id},
    )

    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully",
        "user_id": user_id,
        "is_active": is_active,
    }

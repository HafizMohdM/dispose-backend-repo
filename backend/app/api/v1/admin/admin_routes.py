from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.permissions import require_permission
from app.core.dependencies import get_db
from app.models.user import User
from app.models.role import Role
from app.models.role_mapping import UserRole
from app.services.audit_service import log_event
from app.repositories.admin_user_repo import AdminUserRepository
from app.services.admin_provision_service import AdminProvisionService
from app.api.v1.admin.admin_schemas import (
    BulkInviteRequest,
    InvitationResponse,
    UserListCursorResponse,
    DirectUserCreate,
)

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


def get_org_id(current_user: User) -> int:
    org_id = getattr(current_user, "current_org_id", getattr(current_user, "organization_id", None))
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context is required."
        )
    return org_id

@router.get("/users", response_model=UserListCursorResponse)
def list_users_cursor(
    request: Request,
    search: Optional[str] = Query(None, description="Search by email or role"),
    role: Optional[str] = Query(None, description="Filter by exact role name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, last_login_at, email, id)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    last_seen_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
):
    """
    List users with dynamic sorting, filtering, and deterministic cursor/offset pagination.
    Enforces multi-tenant isolation.
    """
    org_id = get_org_id(current_user)
    repo = AdminUserRepository(db)
    
    # Validate sort parameters
    valid_sorts = {"created_at", "last_login_at", "email", "id"}
    if sort_by not in valid_sorts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort_by. Allowed: {valid_sorts}")
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_order. Allowed: asc, desc")

    users, has_more = repo.get_users_cursor_paginated(
        org_id, last_seen_id, limit, search, role, is_active, sort_by, sort_order
    )
    
    if sort_by == "id":
        next_cursor = users[-1].id if users else None
    else:
        # Pass the offset as the next cursor if not keyset paginating by id
        next_cursor = (last_seen_id or 0) + limit if has_more else None
    
    return UserListCursorResponse(
        users=[
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
        next_cursor=next_cursor if has_more else None,
        has_more=has_more
    )


@router.post("/users")
def create_direct_user(
    request_data: DirectUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage")),
):
    """
    Direct single-user provisioning API for explicit staff creation
    bypassing the asynchronous invitation flow.
    """
    ip_address = request.client.host if request.client else None
    org_id = get_org_id(current_user)
    
    # 1. Resolve role
    role = db.query(Role).filter(Role.name == request_data.role.upper()).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{request_data.role}' not found")
        
    # 2. Check if user exists by mobile or email
    user = db.query(User).filter((User.mobile == request_data.mobile) | (User.email == request_data.email.lower())).first()
    if user:
        # Prevent stealing user contexts across organizations silently if already in org
        existing_mapping = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.org_id == org_id).first()
        if existing_mapping:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists in this organization")
        
        # Attach missing email if provided
        if not user.email and request_data.email:
            user.email = request_data.email.lower()
    else:
        user = User(
            mobile=request_data.mobile,
            email=request_data.email.lower(),
            is_active=request_data.is_active
        )
        db.add(user)
        db.flush()
        
    # 3. Create mapping
    mapping = UserRole(
        user_id=user.id,
        role_id=role.id,
        org_id=org_id
    )
    db.add(mapping)
    
    db.commit()
    
    log_event(
        db,
        current_user.id,
        "ADMIN_DIRECT_USER_CREATE",
        org_id=org_id,
        metadata={
            "target_user_id": user.id, 
            "actor_user_id": current_user.id,
            "org_id": org_id,
            "role": role.name,
            "ip_address": ip_address
        }
    )
    
    return {
        "message": "User provisioned successfully",
        "user_id": user.id,
        "mobile": user.mobile,
        "role": role.name
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.access")),
):
    """
    Update a user's role for a specific organization
    """
    ip_address = request.client.host if request.client else None

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
        metadata={
            "target_user_id": user_id, 
            "new_role": role_name,
            "actor_user_id": current_user.id,
            "org_id": org_id,
            "ip_address": ip_address
        },
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.access")),
):
    """
    Activate or deactivate a user account
    """
    ip_address = request.client.host if request.client else None
    org_id = get_org_id(current_user)

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

    log_event(
        db,
        current_user.id,
        "ADMIN_USER_ACTIVATED" if is_active else "ADMIN_USER_DEACTIVATED",
        metadata={
            "target_user_id": user_id,
            "actor_user_id": current_user.id,
            "org_id": org_id,
            "ip_address": ip_address
        },
        org_id=org_id
    )

    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully",
        "user_id": user_id,
        "is_active": is_active,
    }


@router.post("/invitations/bulk", response_model=list[InvitationResponse])
def bulk_invite_users(
    request_data: BulkInviteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.super")),
):
    """
    Atomic bulk invitation provisioning with rollback capabilities.
    Max 200 invites per batch.
    """
    ip_address = request.client.host if request.client else None
    if len(request_data.invites) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk invitation size exceeds the maximum limit of 200."
        )
        
    org_id = get_org_id(current_user)
    service = AdminProvisionService(db)
    result = service.bulk_provision_staff(org_id, request_data.invites)
    
    log_event(
        db,
        current_user.id,
        "ADMIN_BULK_INVITE",
        org_id=org_id,
        metadata={
            "invite_count": len(result),
            "actor_user_id": current_user.id,
            "org_id": org_id,
            "ip_address": ip_address
        }
    )
    
    return result


@router.get("/invitations/verify/{token}", response_model=InvitationResponse)
def verify_invitation_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Cryptographically verify invitation tokens. Public route but consumes high-entropy tokens.
    """
    service = AdminProvisionService(db)
    return service.verify_invitation(token)

@router.delete("/invitations/expired")
def cleanup_expired_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin.super")),
):
    """
    Automatic cleanup for expired invitations.
    Maintains org isolation and idempotent behavior.
    """
    org_id = get_org_id(current_user)
    
    from app.services.invitation_service import InvitationService
    service = InvitationService(db)
    deleted_count = service.cleanup_expired_invitations(org_id)
    
    log_event(
        db,
        current_user.id,
        "INVITATION_EXPIRED",
        org_id=org_id,
        metadata={
            "deleted_count": deleted_count,
            "actor_user_id": current_user.id,
            "org_id": org_id
        }
    )
    
    return {"message": f"Successfully cleaned up {deleted_count} expired invitations", "deleted_count": deleted_count}

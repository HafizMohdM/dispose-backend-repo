from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.v1.auth.auth_schemas import RequestOTP, VerifyOTP, UpdateProfileRequest
from app.api.v1.auth.auth_service import (
    request_otp,
    verify_otp,
    get_active_sessions,
    revoke_session,
    rotate_refresh_token,
    purge_expired_sessions,
)
from app.core.database import SessionLocal

from app.core.dependencies import get_current_user, get_db
from app.core.security import create_access_token

from app.models.user import User, UserSession
from app.models.role import Role
from app.models.role_mapping import UserRole, RolePermission
from app.models.organization import Organization
from app.models.role import Permission
from app.services.audit_service import log_event

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request-otp")
def request_otp_api(payload: RequestOTP, db: Session = Depends(get_db)):
    otp = request_otp(db, payload.mobile)
    return {"message": "OTP sent", "otp": otp}  # REMOVE otp later


@router.post("/verify-otp")
def verify_otp_api(payload: VerifyOTP, request: Request, db: Session = Depends(get_db)):
    # CRITICAL 4 — Extract session metadata from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device_name = request.headers.get("x-device-name")

    result = verify_otp(
        db, payload.mobile, payload.otp,
        ip_address=ip_address,
        device_name=device_name,
        user_agent=user_agent,
    )
    if not result:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    return result


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all active sessions for the current user.
    """
    sessions = get_active_sessions(
        db,
        user_id=current_user.id,
        current_session_id=current_user.current_session_id,
    )
    return {"sessions": sessions}


@router.post("/revoke-session/{session_id}")
def revoke_session_api(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke a specific session by ID. Only the session owner can revoke.
    """
    return revoke_session(db, session_id=session_id, user_id=current_user.id)

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "mobile": current_user.mobile,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }

@router.get("/my-organizations")
def get_my_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns list of organizations the current user belongs to,
    along with their role in each organization.
    """

    results = (
        db.query(
            Organization.id.label("org_id"),
            Organization.name.label("org_name"),
            Role.name.label("role"),
            UserRole.created_at.label("joined_at")
        )
        .join(UserRole, UserRole.org_id == Organization.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == current_user.id)
        .all()
    )

    return [
        {
            "org_id": row.org_id,
            "org_name": row.org_name,
            "role": row.role,
            "joined_at": row.joined_at
        }
        for row in results
    ]

@router.post("/select-organization")
def select_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    User selects organization → system issues org-scoped JWT
    """

    user_role = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == current_user.id,
            UserRole.org_id == org_id
        )
        .first()
    )

    if not user_role:
        raise HTTPException(
            status_code=403,
            detail="User does not belong to this organization"
        )

    role = db.query(Role).filter(Role.id == user_role.role_id).first()

    token = create_access_token({
        "user_id": current_user.id,
        "org_id": org_id,
        "role": role.name,
        "session_id": current_user.current_session_id,
        "token_version": current_user.token_version,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "org_id": org_id,
        "role": role.name
    }

@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout current session only (soft revoke)
    """

    session = db.query(UserSession).filter(
        UserSession.id == current_user.current_session_id,
        UserSession.user_id == current_user.id,
    ).first()

    if session:
        session.expires_at = __import__('datetime').datetime.utcnow()
        db.commit()

    log_event(
        db, current_user.id, "LOGOUT",
        session_id=current_user.current_session_id,
    )

    return {
        "message": "Logged out successfully"
    }

@router.post("/refresh-token")
def refresh_token(
    current_user: User = Depends(get_current_user),
):
    """
    Issue a new JWT using current tenant context
    """

    if not current_user.current_org_id:
        raise HTTPException(
            status_code=400,
            detail="Organization context missing"
        )

    new_token = create_access_token({
        "user_id": current_user.id,
        "org_id": current_user.current_org_id,
        "role": current_user.current_role,
        "session_id": current_user.current_session_id,
        "token_version": current_user.token_version,
    })

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "org_id": current_user.current_org_id,
        "role": current_user.current_role,
    }

@router.post("/rotate-refresh-token")
def rotate_refresh_token_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rotate refresh token and issue new access token.
    Client must send current refresh token in request body.
    """
    # Get the current session's refresh token for rotation
    session = db.query(UserSession).filter(
        UserSession.id == current_user.current_session_id,
        UserSession.user_id == current_user.id,
    ).first()

    if not session or not session.refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token for current session")

    return rotate_refresh_token(db, session.refresh_token, current_user.id)

@router.get("/profile")
def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Returns authenticated user's profile and current tenant context
    """

    return {
        "user": {
            "id": current_user.id,
            "mobile": current_user.mobile,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
        "tenant": {
            "org_id": current_user.current_org_id,
            "role": current_user.current_role,
        }
    }

@router.patch("/profile")
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user's profile fields safely
    """

    if payload.email is not None:
        current_user.email = payload.email

    db.commit()
    db.refresh(current_user)

    log_event(db, current_user.id, "PROFILE_UPDATED")

    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "mobile": current_user.mobile,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "updated_at": current_user.updated_at,
        }
    }

@router.post("/deactivate-account")
def deactivate_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft deactivate user account
    """

    if not current_user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Account already inactive"
        )

    current_user.is_active = False

    # also revoke all sessions + invalidate tokens
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).delete()

    current_user.token_version += 1

    db.commit()

    log_event(db, current_user.id, "ACCOUNT_DEACTIVATED")

    return {
        "message": "Account deactivated successfully"
    }

@router.post("/logout-all-devices")
def logout_all_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout user from all devices by deleting all session records
    and incrementing token_version to invalidate all outstanding JWTs.
    """

    deleted = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id)
        .delete()
    )

    # CRITICAL 3 — Increment token_version to invalidate ALL issued JWTs
    current_user.token_version += 1

    db.commit()

    log_event(db, current_user.id, "LOGOUT_ALL_DEVICES")

    return {
        "message": "Logged out from all devices successfully",
        "sessions_revoked": deleted
    }

@router.delete("/sessions/expired")
def cleanup_expired_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Purge all expired sessions from the database.
    """
    result = purge_expired_sessions(db)
    return result

@router.get("/permissions")
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the current user's role and associated permissions
    """

    role_name = current_user.current_role

    if not role_name:
        return {"role": None, "permissions": []}

    permissions = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .filter(Role.name == role_name)
        .all()
    )

    return {
        "role": role_name,
        "permissions": [p.code for p in permissions],
    }
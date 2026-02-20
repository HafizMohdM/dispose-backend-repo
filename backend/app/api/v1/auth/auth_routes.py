from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.auth.auth_schemas import RequestOTP, VerifyOTP, UpdateProfileRequest
from app.api.v1.auth.auth_service import request_otp, verify_otp
from app.core.database import SessionLocal

from app.core.dependencies import get_current_user,get_db
from app.core.security import create_access_token

from app.core.security import create_access_token

from app.models.user import User , UserSession
from app.models.role import Role
from app.models.role_mapping import UserRole
from app.models.organization import Organization

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
def verify_otp_api(payload: VerifyOTP, db: Session = Depends(get_db)):
    token = verify_otp(db, payload.mobile, payload.otp)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    return {"access_token": token}

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
        "role": role.name
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
    Logout current user by invalidating all active sessions
    """

    db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).delete()

    db.commit()

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
    })

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "org_id": current_user.current_org_id,
        "role": current_user.current_role,
    }

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

    # also revoke all sessions
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).delete()

    db.commit()

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
    """

    deleted = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id)
        .delete()
    )

    db.commit()

    return {
        "message": "Logged out from all devices successfully",
        "sessions_revoked": deleted
    }
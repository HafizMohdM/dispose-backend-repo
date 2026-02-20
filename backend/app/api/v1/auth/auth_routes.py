from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.auth.auth_schemas import RequestOTP, VerifyOTP
from app.api.v1.auth.auth_service import request_otp, verify_otp
from app.core.database import SessionLocal

from app.core.dependencies import get_current_user,get_db

from app.core.security import create_access_token

from app.models.user import User
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


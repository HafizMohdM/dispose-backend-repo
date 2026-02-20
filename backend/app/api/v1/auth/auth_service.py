from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User, UserSession
from app.models.role import Role
from app.models.role_mapping import UserRole

from app.core.security import (
    generate_otp,
    hash_otp,
    create_access_token,
)

from app.core.config import OTP_EXPIRY_MINUTES


# ---------------------------------------------------
# Assign default role to user (production requirement)
# ---------------------------------------------------
def assign_default_role(db: Session, user_id: int, org_id: int = 1):
    """
    Assign CUSTOMER role to user if no role exists for the org.
    Safe to call multiple times.
    """

    existing = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_id,
            UserRole.org_id == org_id,
        )
        .first()
    )

    if existing:
        return

    default_role = (
        db.query(Role)
        .filter(Role.name == "CUSTOMER")
        .first()
    )

    if not default_role:
        raise Exception("Default role CUSTOMER not found")

    user_role = UserRole(
        user_id=user_id,
        role_id=default_role.id,
        org_id=org_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(user_role)
    db.commit()


# ---------------------------------------------------
# Request OTP
# ---------------------------------------------------
def request_otp(db: Session, mobile: str):
    otp = generate_otp()
    hashed = hash_otp(otp)

    user = db.query(User).filter(User.mobile == mobile).first()

    if not user:
        user = User(
            mobile=mobile,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    session = UserSession(
        user_id=user.id,
        token=hashed,
        expires_at=datetime.utcnow()
        + timedelta(minutes=OTP_EXPIRY_MINUTES),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(session)
    db.commit()

    # For testing only. Production should send via SMS
    return otp


# ---------------------------------------------------
# Verify OTP and generate JWT
# ---------------------------------------------------
def verify_otp(db: Session, mobile: str, otp: str):

    user = db.query(User).filter(User.mobile == mobile).first()

    if not user:
        return None

    hashed = hash_otp(otp)

    session = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.token == hashed,
            UserSession.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not session:
        return None

    # Assign default role automatically
    assign_default_role(db, user.id, org_id=1)

    # Generate JWT
    token = create_access_token(
        {
            "user_id": user.id,
        }
    )

    return token

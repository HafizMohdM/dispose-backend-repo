from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User, UserSession
from app.models.role import Role
from app.models.role_mapping import UserRole

from app.core.security import (
    generate_otp,
    hash_otp,
    create_access_token,
    generate_refresh_token,
)

from app.core.config import OTP_EXPIRY_MINUTES
from app.services.audit_service import log_event

OTP_RATE_LIMIT = 5
OTP_RATE_WINDOW_MINUTES = 15


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
        # Auto-create the role to prevent 500 errors
        default_role = Role(
            name="CUSTOMER",
            description="Organization customer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(default_role)
        db.commit()
        db.refresh(default_role)

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

    # RATE LIMIT CHECK
    window_start = datetime.utcnow() - timedelta(minutes=OTP_RATE_WINDOW_MINUTES)

    otp_count = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.created_at >= window_start,
        )
        .count()
    )

    if otp_count >= OTP_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Try again later.",
        )

    otp = generate_otp()
    hashed = hash_otp(otp)

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
MAX_OTP_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
MAX_FAILED_LOGIN_ATTEMPTS = 5


def verify_otp(db: Session, mobile: str, otp: str, ip_address: str = None,
               device_name: str = None, user_agent: str = None):

    user = db.query(User).filter(User.mobile == mobile).first()

    if not user:
        return None

    # ADDITION 3 — Block deactivated accounts at login
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is deactivated. Contact support.",
        )

    # OTP lockout protection — check if user is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Account locked due to too many failed attempts. Try again in {remaining} minutes.",
        )

    hashed = hash_otp(otp)

    # Find the latest non-expired OTP session for this user
    otp_session = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.expires_at > datetime.utcnow(),
        )
        .order_by(UserSession.created_at.desc())
        .first()
    )

    if not otp_session:
        raise HTTPException(status_code=401, detail="No active OTP session")

    if otp_session.failed_attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=429, detail="OTP attempts exceeded")

    if otp_session.token != hashed:
        otp_session.failed_attempts += 1

        # Increment user-level failed login attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

        # Lock account if threshold reached
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

        db.commit()
        log_event(db, user.id, "LOGIN_FAILED")
        raise HTTPException(status_code=401, detail="Invalid OTP")

    # === SUCCESS PATH ===

    # Reset failed attempts on success (both session-level and user-level)
    user.failed_login_attempts = 0
    user.locked_until = None

    # Expire the OTP session — it is consumed
    otp_session.expires_at = datetime.utcnow()
    db.commit()

    # Assign default role automatically
    assign_default_role(db, user.id, org_id=1)

    # CRITICAL 1 — Create a NEW authenticated session (not reuse OTP session)
    from app.core.config import JWT_EXPIRE_HOURS, JWT_EXPIRE_MINUTES
    refresh_tok = generate_refresh_token()
    # Use hash of refresh token as session token (unique per session)
    session_token = hash_otp(refresh_tok)
    auth_session = UserSession(
        user_id=user.id,
        token=session_token,
        refresh_token=refresh_tok,
        expires_at=datetime.utcnow() + timedelta(
            hours=int(JWT_EXPIRE_HOURS), minutes=int(JWT_EXPIRE_MINUTES)
        ),
        ip_address=ip_address,
        device_name=device_name,
        user_agent=user_agent,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)

    # Generate JWT — include session_id and token_version
    token = create_access_token(
        {
            "user_id": user.id,
            "session_id": auth_session.id,
            "token_version": user.token_version,
        }
    )

    # Update last_login_at AFTER session created and JWT issued
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Audit log
    log_event(
        db, user.id, "LOGIN_SUCCESS",
        session_id=auth_session.id,
        ip_address=ip_address,
    )

    return {
        "access_token": token,
        "refresh_token": refresh_tok,
    }


# ---------------------------------------------------
# Get active sessions for user
# ---------------------------------------------------
def get_active_sessions(db: Session, user_id: int, current_session_id: int):
    """
    Return all active (non-expired) sessions for the user.
    Marks which session is the current one via session_id comparison.
    """
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow(),
        )
        .order_by(UserSession.created_at.desc())
        .all()
    )

    return [
        {
            "session_id": s.id,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "ip_address": s.ip_address,
            "device_name": s.device_name,
            "user_agent": s.user_agent,
            "is_current_session": s.id == current_session_id,
        }
        for s in sessions
    ]


# ---------------------------------------------------
# Revoke a specific session (soft revocation)
# ---------------------------------------------------
def revoke_session(db: Session, session_id: int, user_id: int):
    """
    Soft-revoke a session by setting expires_at to now.
    Only the session owner can revoke. Preserves audit trail.
    """
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found or not owned by user",
        )

    # Soft revocation — set expiry to now
    session.expires_at = datetime.utcnow()
    db.commit()

    # Audit log
    log_event(
        db,
        user_id,
        "SESSION_REVOKED",
        session_id=session_id,
    )

    return {"message": "Session revoked successfully", "session_id": session_id}


# ---------------------------------------------------
# Refresh token rotation
# ---------------------------------------------------
def rotate_refresh_token(db: Session, old_refresh_token: str, user_id: int):
    """
    Validate refresh token, rotate it, and issue a new access token.
    The old refresh token is invalidated.
    """
    session = (
        db.query(UserSession)
        .filter(
            UserSession.refresh_token == old_refresh_token,
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    # Rotate: issue new refresh token, invalidate old
    new_refresh = generate_refresh_token()
    session.refresh_token = new_refresh

    # Extend session expiry
    from app.core.config import JWT_EXPIRE_HOURS, JWT_EXPIRE_MINUTES
    session.expires_at = datetime.utcnow() + timedelta(
        hours=int(JWT_EXPIRE_HOURS), minutes=int(JWT_EXPIRE_MINUTES)
    )
    session.updated_at = datetime.utcnow()
    db.commit()

    # Issue new access token
    new_access = create_access_token(
        {
            "user_id": user.id,
            "session_id": session.id,
            "token_version": user.token_version,
        }
    )

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
    }


# ---------------------------------------------------
# Purge expired sessions
# ---------------------------------------------------
def purge_expired_sessions(db: Session):
    """
    Delete all expired sessions from the database.
    Call periodically or via admin endpoint.
    """
    deleted = (
        db.query(UserSession)
        .filter(UserSession.expires_at <= datetime.utcnow())
        .delete()
    )
    db.commit()
    return {"purged": deleted}

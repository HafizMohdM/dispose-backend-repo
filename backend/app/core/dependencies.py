from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM
from app.core.database import SessionLocal
from app.models.user import User, UserSession
from app.models.role_mapping import UserRole
from app.models.organization import Organization
from datetime import datetime

security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        user_id = payload.get("user_id")
        org_id = payload.get("org_id")
        role = payload.get("role")
        session_id = payload.get("session_id")
        jwt_token_version = payload.get("token_version", 0)

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # CRITICAL 2 — Require session_id in JWT
        if session_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing session_id. Please login again.",
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Token version enforcement — reject if mismatch
    if jwt_token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated. Please login again.",
        )

    # Session expiration enforcement — validate specific session by ID
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user.id,
        UserSession.expires_at > datetime.utcnow(),
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or revoked",
        )

    # ADDITION 4 — Tenant context enforcement
    if org_id is not None:
        membership = (
            db.query(UserRole)
            .filter(
                UserRole.user_id == user.id,
                UserRole.org_id == org_id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to this organization",
            )

    # CRITICAL: attach tenant context and session context to user object
    user.current_org_id = org_id
    user.current_role = role
    user.current_session_id = session.id

    return user


def get_current_organization(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.organization import Organization

    org_id = getattr(current_user, "current_org_id", None)

    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context in token. Please login with an organization.",
        )

    organization = db.query(Organization).filter(Organization.id == org_id).first()

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


def get_user_org(db: Session, user: User) -> Organization:
    user_role = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization",
        )
    org = db.query(Organization).filter(Organization.id == user_role.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org

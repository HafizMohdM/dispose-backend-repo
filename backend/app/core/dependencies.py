from fastapi import Depends, HTTPException, status, Response
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


class UsageEnforcer:
    """
    Reusable FastAPI Dependency to enforce subscription usage limits.
    Prevents creation of new resources (pickups, drivers, etc.) if quotas are exceeded.
    Supports soft limits (warnings via response headers) vs hard limits (HTTP 403 blocks).
    """
    def __init__(self, resource: str, soft_limit: bool = False, threshold: float = 0.85, increment: int = 1):
        self.resource = resource # e.g. "pickups", "drivers", "weight"
        self.soft_limit = soft_limit
        self.threshold = threshold
        self.increment = increment

    def __call__(
        self,
        response: Response,
        db: Session = Depends(get_db),
        current_user = Depends(get_current_user)
    ):
        from app.repositories.subscription_repo import SubscriptionRepository
        from app.models.subscription import SubscriptionStatus
        
        org_id = getattr(current_user, "current_org_id", None)
        if org_id is None:
            # Fallback to UserRole mapping
            from app.models.role_mapping import UserRole
            role_map = db.query(UserRole).filter(UserRole.user_id == current_user.id).first()
            if role_map:
                org_id = role_map.org_id
                
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No organization context found."
            )
            
        sub = SubscriptionRepository.get_latest_subscription(db, org_id)
        if not sub or sub.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE]:
            detail_msg = "No active subscription found. Please subscribe to a plan."
            if sub and sub.status == SubscriptionStatus.SUSPENDED:
                detail_msg = "Your subscription has been suspended due to outstanding payment. Please complete payment to restore access."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_msg
            )
            
        if datetime.utcnow() > sub.end_date:
            SubscriptionRepository.update_subscription_status(db, sub.id, SubscriptionStatus.EXPIRED)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription has expired."
            )
            
        usage = SubscriptionRepository.get_usage(db, sub.id)
        if not usage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription usage record not found."
            )
            
        # Get limit and current usage based on resource type
        limit = 0
        used = 0
        
        if self.resource == "pickups":
            limit = sub.plan.pickup_limit
            used = usage.pickups_used
        elif self.resource == "drivers":
            limit = sub.plan.driver_limit
            used = usage.drivers_used
        elif self.resource == "weight":
            limit = sub.plan.waste_weight_limit
            used = float(usage.waste_weight_used)
            
        # If no limit is configured, allow the request to proceed
        if limit <= 0:
            return sub
            
        # 1. Soft Limit Check: Add warnings if usage is near or exceeds threshold
        usage_pct = (used + self.increment) / limit if limit > 0 else 0
        
        if usage_pct >= self.threshold:
            response.headers["X-Quota-Warning"] = (
                f"Your organization has consumed {used}/{limit} of its plan {self.resource} limit "
                f"({usage_pct*100:.1f}%). Please consider upgrading soon."
            )
            
        # 2. Hard/Soft Limit breach check
        if used + self.increment > limit:
            response.headers["X-Quota-Limit-Breached"] = "true"
            if self.soft_limit:
                # For soft limit, only warn and allow action to proceed
                response.headers["X-Quota-Warning"] = (
                    f"Soft quota limit breached for {self.resource}! "
                    f"Current usage is {used}/{limit}. Please upgrade your plan."
                )
            else:
                # For hard limit, block the request
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"You have reached your plan's maximum of {limit} {self.resource}. "
                        f"Please upgrade your subscription to execute this action."
                    )
                )
                
        return sub

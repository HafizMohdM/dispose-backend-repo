from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.dependencies import get_current_user, get_user_org
from app.api.v1.subscriptions.subscription_schemas import PaymentHistoryResponse, RefundRequest
from app.services.payment_service import PaymentService

router = APIRouter()

@router.get("/history", response_model=PaymentHistoryResponse)
def get_payment_history(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.view"))
):
    """
    Returns payment history for the organization. Administrators with 'subscription.manage' get global payment logs.
    """
    from app.models.role_mapping import UserRole
    # Check if user has admin privileges
    is_admin = False
    try:
        # Determine if user is super admin or admin
        roles = [r.name for r in current_user.roles]
        if "super_admin" in roles or "admin" in roles:
            is_admin = True
    except AttributeError:
        pass
        
    org = get_user_org(db, current_user)
    return PaymentService.get_payment_history(db, org.id, is_admin)

@router.post("/refund")
def refund_payment(
    request: RefundRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("subscription.manage"))
):
    """
    Allows administrators to process a refund for a transaction.
    """
    return PaymentService.refund_payment(db, request.payment_id)

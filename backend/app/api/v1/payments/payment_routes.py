import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.core.dependencies import get_db, get_current_user, get_user_org
from app.core.permissions import require_permission
from app.services.subscription_service import SubscriptionService
from app.api.v1.payments.payment_schemas import (
    InvoiceResponse,
    PaginatedInvoiceResponse,
    PaymentInitiateRequest,
    PaymentRetryRequest,
    PaymentInitiateResponse,
    PaymentResponse,
    WebhookRequest
)
from app.services.payment_service import PaymentService

router = APIRouter()

@router.get("/invoices", response_model=List[InvoiceResponse])
def get_my_invoices(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.view"))
):
    """Get all invoices for the current user's organization"""
    if getattr(current_user, "is_system_admin", False):
        # Admins can be handled differently, but here we enforce org-level scoping
        pass
    
    org = get_user_org(db, current_user)
    invoices = PaymentService.get_my_invoices(db, org.id)
    return invoices

@router.get("/invoices/{id}", response_model=InvoiceResponse)
def get_invoice(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.view"))
):
    """Get a specific invoice"""
    # Assuming admins have is_superadmin attribute or similar, or we just rely on rbac
    is_admin = getattr(current_user, "is_system_admin", False) 
    org = get_user_org(db, current_user)
    return PaymentService.get_invoice(db, id, org.id, is_admin=is_admin)

@router.get("/invoices/{id}/download")
def download_invoice_pdf(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.view"))
):
    """
    Download the tax invoice as a PDF file.
    Includes comprehensive GST calculations and company details.
    """
    is_admin = getattr(current_user, "is_system_admin", False) 
    org = get_user_org(db, current_user)
    
    pdf_buffer = PaymentService.generate_invoice_pdf(db, id, org.id, is_admin=is_admin)
    filename = f"invoice_{str(id)[:8]}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(
    request: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.manage"))
):
    """
    Initiate a new payment for a pending invoice.
    Returns the session checkout info.
    """
    org = get_user_org(db, current_user)
    return PaymentService.initiate_payment(
        db=db,
        invoice_id=request.invoice_id,
        gateway=request.gateway,
        organization_id=org.id
    )

@router.post("/invoices/{invoice_id}/retry", response_model=PaymentInitiateResponse)
def retry_payment(
    invoice_id: uuid.UUID,
    request: PaymentRetryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.manage"))
):
    """
    Retry a FAILED or PENDING invoice payment by creating a fresh payment intent.
    """
    org = get_user_org(db, current_user)
    return PaymentService.retry_payment(
        db=db,
        invoice_id=invoice_id,
        gateway=request.gateway,
        organization_id=org.id
    )

@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive payment updates from gateways (Stripe/Razorpay).
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    try:
        request_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    return PaymentService.process_webhook(
        db=db,
        signature=signature,
        request_data=request_data,
        raw_body=body
    )

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_status(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.view"))
):
    """Get the status of a specific payment attempt"""
    from app.repositories.payment_repo import PaymentRepository
    payment = PaymentRepository.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    invoice = payment.invoice
    is_admin = getattr(current_user, "is_system_admin", False)
    
    if invoice and not is_admin:
        org = get_user_org(db, current_user)
        if invoice.organization_id != org.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this payment")
        
    return payment

@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("payment.manage"))
):
    """
    Refund a successful payment. This revokes the active subscription gracefully.
    Restricted to Admins (`payment.manage` permission).
    """
    # current_user is guaranteed to have payment.manage (Admin) via dependency
    return PaymentService.refund_payment(
        db=db,
        payment_id=payment_id,
        admin_user_id=current_user.id
    )

@router.post("/cron/renew-subscriptions")
def renew_subscriptions(
    db: Session = Depends(get_db),
    # In a real app we might use a dedicated cron API key or rely on internal network rules.
    # Here we simulate with an admin permission requirement for manual triggering.
    current_user = Depends(require_permission("payment.manage"))
):
    """
    CRON Endpoint: Sweeps for expired subscriptions and automatically provisions new PENDING subscriptions and invoices.
    """
    return SubscriptionService.renew_expired_subscriptions(db)

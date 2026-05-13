import uuid
import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

import razorpay
from app.core.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentStatus
from app.models.subscription import SubscriptionStatus
from app.models.subscription_usage import SubscriptionUsage
from app.repositories.payment_repo import PaymentRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.services.audit_service import AuditService
from app.core.pubsub import pubsub_service
from app.services.realtime.realtime_dashboard_service import dashboard_throttler
import asyncio


class PaymentService:
    
    @staticmethod
    def initiate_payment(db: Session, invoice_id: uuid.UUID, gateway: str, organization_id: int):
        invoice = PaymentRepository.get_invoice_by_id(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")

        if invoice.status != InvoiceStatus.PENDING:
            raise HTTPException(status_code=400, detail="Invoice is not in PENDING state")

        # Create Razorpay order (amount is in paise)
        order = razorpay_client.order.create({
            "amount": int(float(invoice.final_amount) * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        payment = PaymentRepository.create_payment(
            db=db,
            invoice_id=invoice.id,
            amount=float(invoice.final_amount),
            gateway=gateway
        )
        payment.gateway_payment_id = order["id"]

        # Log initiation
        audit_svc = AuditService(db)
        audit_svc.log_action(
            user_id=organization_id,
            action="payment.initiated",
            org_id=organization_id,
            meta={"invoice_id": str(invoice.id), "payment_id": str(payment.id), "gateway": gateway, "order_id": order["id"]}
        )
        
        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment.id,
            "invoice_id": invoice.id,
            "gateway": gateway,
            "amount": float(payment.amount),
            "status": payment.status,
            "session_data": {
                "order_id": order["id"],
                "key": RAZORPAY_KEY_ID,
                "amount": order["amount"],
                "currency": "INR"
            }
        }

    @staticmethod
    def refund_payment(db: Session, payment_id: uuid.UUID, admin_user_id: int):
        # We must use with_for_update to prevent webhooks or retries modifying this concurrently
        payment = PaymentRepository.get_payment_by_id_for_update(db, payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
            
        if payment.status != PaymentStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Only SUCCESS payments can be refunded")

        payment.status = PaymentStatus.REFUNDED
        
        invoice = payment.invoice
        if invoice:
            invoice.status = InvoiceStatus.REFUNDED
            
            if invoice.subscription_id:
                sub = SubscriptionRepository.get_subscription_by_id(db, invoice.subscription_id)
                if sub and sub.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]:
                    # Revoke access
                    sub.status = SubscriptionStatus.CANCELLED
                    sub.cancelled_at = datetime.utcnow()

        audit_svc = AuditService(db)
        org_id = invoice.organization_id if invoice else 0
        audit_svc.log_action(
            user_id=admin_user_id,
            action="payment.refunded",
            org_id=org_id,
            meta={"payment_id": str(payment.id), "invoice_id": str(invoice.id) if invoice else None}
        )
        
        db.commit()
        db.refresh(payment)
        
        return payment

    @staticmethod
    def retry_payment(db: Session, invoice_id: uuid.UUID, gateway: str, organization_id: int):
        invoice = PaymentRepository.get_invoice_by_id(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")

        if invoice.status not in [InvoiceStatus.PENDING, InvoiceStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Only PENDING or FAILED invoices can be retried")

        # Create a new payment record instead of reusing the old one
        payment = PaymentRepository.create_payment(
            db=db,
            invoice_id=invoice.id,
            amount=float(invoice.amount),
            gateway=gateway
        )

        audit_svc = AuditService(db)
        audit_svc.log_action(
            user_id=organization_id,
            action="payment.retried",
            org_id=organization_id,
            meta={"invoice_id": str(invoice.id), "new_payment_id": str(payment.id), "gateway": gateway}
        )
        
        db.commit()
        db.refresh(payment)

        session_url = f"https://mock-gateway.com/checkout/{payment.id}?retry=true"
        
        return {
            "payment_id": payment.id,
            "invoice_id": invoice.id,
            "gateway": gateway,
            "amount": float(payment.amount),
            "status": payment.status,
            "session_data": {"checkout_url": session_url}
        }

    @staticmethod
    def verify_razorpay_signature(body: bytes, signature: str):
        import hmac, hashlib
        from app.core.config import RAZORPAY_WEBHOOK_SECRET
        generated_signature = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)

    @staticmethod
    def process_webhook(db: Session, signature: str, request_data: dict, raw_body: bytes = b"", webhook_timestamp: int = None):
        """
        Enterprise-grade webhook processor with Security, Audit, and Financial Integrity layers.
        """
        import hmac
        import hashlib
        import time
        import os

        # 1. Webhook Security Specification: Replay Attack Prevention
        if webhook_timestamp:
            current_time = int(time.time())
            if abs(current_time - webhook_timestamp) > 300: # 5 min tolerance
                raise HTTPException(status_code=400, detail="Webhook timestamp outside of tolerance zone (Replay Attack)")

        # 2. Webhook Security Specification: Signature Validation
        if not PaymentService.verify_razorpay_signature(raw_body, signature):
            PaymentRepository.create_payment_event(db, None, signature, "SIGNATURE_FAILED", request_data)
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        event = request_data.get("event")
        if not event:
            return {"status": "ignored"}

        # Extract payment data
        try:
            payment_entity = request_data["payload"]["payment"]["entity"]
        except KeyError:
            # We don't have payment data in this event payload, just ignore
            return {"status": "ignored"}

        order_id = payment_entity.get("order_id")
        amount_paid = int(payment_entity.get("amount", 0)) # in paise
        gateway_status = payment_entity.get("status", "").upper()

        if not order_id:
            PaymentRepository.create_payment_event(db, None, signature, "MISSING_ORDER_ID", request_data)
            db.commit()
            raise HTTPException(status_code=400, detail="Missing order_id in webhook")

        # Row-level lock to prevent concurrent webhook execution race bugs
        from app.models.payment import Payment
        payment = db.query(Payment).filter(Payment.gateway_payment_id == order_id).with_for_update().first()

        # 3. Payment Event Audit Trail: Log immediately
        payment_event = PaymentRepository.create_payment_event(
            db=db,
            payment_id=payment.id if payment else None,
            signature=signature,
            status="RECEIVED",
            payload=request_data
        )

        if not payment:
            payment_event.processing_status = "PAYMENT_NOT_FOUND"
            db.commit()
            raise HTTPException(status_code=404, detail="Payment not found")

        # 4. Idempotency Check
        if payment.status in [PaymentStatus.SUCCESS, PaymentStatus.REFUNDED, PaymentStatus.DISPUTED]:
            payment_event.processing_status = "IGNORED_DUPLICATE_OR_FROZEN"
            db.commit()
            return {"status": "Already processed", "payment_status": payment.status}

        if payment.status == PaymentStatus.FAILED and event != "payment.captured" and gateway_status != "CAPTURED":
            payment_event.processing_status = "IGNORED_ALREADY_FAILED"
            db.commit()
            return {"status": "Already failed", "payment_status": payment.status}

        invoice = payment.invoice
        if not invoice:
            payment_event.processing_status = "INVOICE_NOT_FOUND"
            db.commit()
            raise HTTPException(status_code=404, detail="Associated invoice not found")
        
        payment.raw_response = request_data

        # 5. Chargeback Handling
        if gateway_status == "DISPUTED" or request_data.get("type") == "chargeback.created":
            payment.status = PaymentStatus.DISPUTED
            payment_event.processing_status = "DISPUTED"
            
            if invoice.subscription_id:
                sub = SubscriptionRepository.get_subscription_by_id(db, invoice.subscription_id)
                if sub and sub.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE]:
                    sub.status = SubscriptionStatus.SUSPENDED
                    
            db.commit()
            return {"status": "Dispute registered and subscription suspended", "payment_id": str(payment.id)}

        # 6. Invoice Financial Integrity Rules
        # Razorpay sends amount in paise, so we multiply our final_amount by 100
        expected_paise = int(float(invoice.final_amount) * 100)
        
        if event == "payment.captured" or gateway_status == "CAPTURED":
            if amount_paid < expected_paise:
                payment.status = PaymentStatus.FAILED
                payment_event.processing_status = "UNDERPAYMENT_FAILED"
                db.commit()
                # Do not change invoice status, it remains PENDING or FAILED for retry
                return {"status": "amount_mismatch"}
            
            elif amount_paid > expected_paise:
                # In strict SaaS, overpayments are flagged and failed to avoid unallocated credit liability
                payment.status = PaymentStatus.FAILED
                payment_event.processing_status = "OVERPAYMENT_ANOMALY"
                db.commit()
                return {"status": "amount_mismatch"}

        audit_svc = AuditService(db)

        if event == "payment.captured" or gateway_status == "CAPTURED":
            # Exact Match Success logic
            payment.status = PaymentStatus.SUCCESS
            payment_event.processing_status = "SUCCESS_PROCESSED"
            
            # Multi-Payment Attempt Handling: Cancel stale initiated payments
            all_payments = PaymentRepository.get_payments_by_invoice(db, invoice.id)
            for p in all_payments:
                if p.id != payment.id and p.status == PaymentStatus.INITIATED:
                    p.status = PaymentStatus.CANCELLED
            
            # Update Invoice
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()
            
            # Update Subscription if applicable
            if invoice.subscription_id:
                sub = SubscriptionRepository.get_subscription_by_id(db, invoice.subscription_id)
                if sub and sub.status in [SubscriptionStatus.PENDING, SubscriptionStatus.EXPIRED, SubscriptionStatus.GRACE]:
                    sub.status = SubscriptionStatus.ACTIVE
                    
                    from app.models.subscription_plan import BillingCycle
                    now = datetime.utcnow()
                    from datetime import timedelta
                    if sub.plan.billing_cycle == BillingCycle.MONTHLY:
                        end_date = now + timedelta(days=30)
                    else:
                        end_date = now + timedelta(days=365)
                        
                    sub.start_date = now
                    sub.end_date = end_date
                    
                    usage = SubscriptionUsage(subscription_id=sub.id)
                    SubscriptionRepository.create_usage_record(db, usage)

            audit_svc.log_action(
                user_id=invoice.organization_id,
                action="payment.success",
                org_id=invoice.organization_id,
                meta={"payment_id": str(payment.id), "invoice_id": str(invoice.id)}
            )

            # Broadcast Realtime Event
            asyncio.create_task(pubsub_service.publish(
                f"analytics:org_{invoice.organization_id}",
                {
                    "event": "payment_success",
                    "organization_id": invoice.organization_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "payment_id": str(payment.id),
                        "amount": float(payment.amount),
                        "status": "success"
                    }
                }
            ))
            
            # Broadcast Revenue Update Event
            asyncio.create_task(pubsub_service.publish(
                f"analytics:org_{invoice.organization_id}",
                {
                    "event": "revenue_updated",
                    "organization_id": invoice.organization_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "increment": float(payment.amount)
                    }
                }
            ))

            # Trigger Live Dashboard KPI Refresh
            asyncio.create_task(dashboard_throttler.trigger_update(db, invoice.organization_id))
            
        elif event == "payment.failed" or gateway_status == "FAILED":
            payment.status = PaymentStatus.FAILED
            invoice.status = InvoiceStatus.FAILED
            payment_event.processing_status = "FAILED_PROCESSED"
            
            audit_svc.log_action(
                user_id=invoice.organization_id,
                action="payment.failed",
                org_id=invoice.organization_id,
                meta={"payment_id": str(payment.id), "invoice_id": str(invoice.id)}
            )

            # Broadcast Realtime Event
            asyncio.create_task(pubsub_service.publish(
                f"analytics:org_{invoice.organization_id}",
                {
                    "event": "payment_failed",
                    "organization_id": invoice.organization_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "payment_id": str(payment.id),
                        "status": "failed"
                    }
                }
            ))
        else:
            payment_event.processing_status = "UNKNOWN_GATEWAY_STATUS"
            db.commit()
            raise HTTPException(status_code=400, detail=f"Unknown gateway status: {gateway_status}")

        db.commit()
        return {"status": "Webhook processed successfully", "payment_id": str(payment.id)}

    @staticmethod
    def get_my_invoices(db: Session, organization_id: int):
        return PaymentRepository.get_invoices_by_org(db, organization_id)

    @staticmethod
    def get_invoice(db: Session, invoice_id: uuid.UUID, organization_id: int, is_admin: bool = False):
        invoice = PaymentRepository.get_invoice_by_id(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not is_admin and invoice.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
        return invoice

    @staticmethod
    def generate_invoice_pdf(db: Session, invoice_id: uuid.UUID, organization_id: int, is_admin: bool = False) -> io.BytesIO:
        invoice = PaymentService.get_invoice(db, invoice_id, organization_id, is_admin)
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Header
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, height - 50, "TAX INVOICE")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 70, "Dispose Waste Management Pvt. Ltd.")
        c.drawString(50, height - 85, "GSTIN: 27AABC1234D1Z5")
        c.drawString(50, height - 100, "123 Green Avenue, Eco Park")
        c.drawString(50, height - 115, "Mumbai, Maharashtra 400001")
        
        # Details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(350, height - 70, f"Invoice #: {str(invoice.id)[:8].upper()}")
        c.setFont("Helvetica", 10)
        c.drawString(350, height - 85, f"Date: {invoice.created_at.strftime('%Y-%m-%d')}")
        c.drawString(350, height - 100, f"Status: {invoice.status.value}")
        if invoice.paid_at:
            c.drawString(350, height - 115, f"Paid On: {invoice.paid_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # Bill To
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 160, "Bill To:")
        c.setFont("Helvetica", 10)
        
        org_name = invoice.organization.name if hasattr(invoice, "organization") and invoice.organization else f"Org ID: {invoice.organization_id}"
        c.drawString(50, height - 175, f"Name: {org_name}")
        c.drawString(50, height - 190, f"Subscription ID: {invoice.subscription_id or 'N/A'}")
        
        # Draw Table Header
        c.line(50, height - 220, 550, height - 220)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(55, height - 235, "Description")
        c.drawString(350, height - 235, "HSN/SAC")
        c.drawString(450, height - 235, "Amount (INR)")
        c.line(50, height - 245, 550, height - 245)
        
        # Tax logic (assuming total amount includes 18% GST)
        total_amount = float(invoice.amount)
        base_amount = total_amount / 1.18
        cgst = base_amount * 0.09
        sgst = base_amount * 0.09
        
        # Item Row
        c.setFont("Helvetica", 10)
        c.drawString(55, height - 265, "Waste Management Subscription")
        c.drawString(350, height - 265, "9994")
        c.drawString(450, height - 265, f"{base_amount:.2f}")
        
        # Subtotals
        c.line(50, height - 320, 550, height - 320)
        c.drawString(350, height - 335, "Taxable Amount:")
        c.drawString(450, height - 335, f"{base_amount:.2f}")
        
        c.drawString(350, height - 350, "CGST (9%):")
        c.drawString(450, height - 350, f"{cgst:.2f}")
        
        c.drawString(350, height - 365, "SGST (9%):")
        c.drawString(450, height - 365, f"{sgst:.2f}")
        
        c.line(350, height - 380, 550, height - 380)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(350, height - 395, "Total Amount:")
        c.drawString(450, height - 395, f"{total_amount:.2f}")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, "This is a computer generated invoice and does not require a physical signature.")
        
        c.showPage()
        c.save()
        
        buffer.seek(0)
        return buffer

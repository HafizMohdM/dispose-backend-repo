import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus, PaymentGateway
from app.models.subscription import Subscription, SubscriptionStatus
from app.main import app

def test_unauthorized_invoice_access(client: TestClient, db: Session, test_user_token: str, test_organization):
    # Create invoice for a *different* org
    invoice_id = uuid4()
    other_org_id = test_organization.id + 999
    db.add(Invoice(
        id=invoice_id,
        organization_id=other_org_id,
        amount=500.0,
        currency="INR",
        status=InvoiceStatus.PENDING,
        due_date="2027-01-01 00:00:00"
    ))
    db.commit()

    resp = client.get(
        f"/api/v1/payments/invoices/{invoice_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    # Token used should correspond to `test_organization`
    assert resp.status_code == 403

def test_initiate_payment_success(client: TestClient, db: Session, test_user_token: str, test_organization):
    invoice_id = uuid4()
    db.add(Invoice(
        id=invoice_id,
        organization_id=test_organization.id,
        amount=1000.0,
        currency="INR",
        status=InvoiceStatus.PENDING,
        due_date="2027-01-01 00:00:00"
    ))
    db.commit()

    # Need payment.manage permission seeded in the test logic, assuming test_user_token has it
    resp = client.post(
        "/api/v1/payments/initiate",
        json={"invoice_id": str(invoice_id), "gateway": "STRIPE"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["gateway"] == "STRIPE"
    assert "checkout_url" in data["session_data"]

def test_webhook_successful_payment(client: TestClient, db: Session, test_organization, test_subscription_plan):
    # Setup Subscription (PENDING) and Invoice (PENDING)
    sub = Subscription(
        organization_id=test_organization.id,
        plan_id=test_subscription_plan.id,
        start_date="2027-01-01 00:00:00",
        end_date="2027-02-01 00:00:00",
        status=SubscriptionStatus.PENDING
    )
    db.add(sub)
    db.flush()

    invoice_id = uuid4()
    invoice = Invoice(
        id=invoice_id,
        organization_id=test_organization.id,
        subscription_id=sub.id,
        amount=test_subscription_plan.price,
        due_date="2027-01-01 00:00:00",
        status=InvoiceStatus.PENDING
    )
    db.add(invoice)
    db.flush()

    payment_id = uuid4()
    payment = Payment(
        id=payment_id,
        invoice_id=invoice_id,
        amount=test_subscription_plan.price,
        gateway=PaymentGateway.RAZORPAY,
        status=PaymentStatus.INITIATED
    )
    db.add(payment)
    db.commit()

    # Trigger webhook
    webhook_payload = {
        "payment_id": str(payment_id),
        "gateway_payment_id": "pay_xyz123",
        "amount": float(test_subscription_plan.price),
        "status": "SUCCESS"
    }
    
    resp = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert resp.status_code == 200

    db.refresh(sub)
    db.refresh(invoice)
    db.refresh(payment)

    # Verification checks
    assert payment.status == PaymentStatus.SUCCESS
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.paid_at is not None
    assert sub.status == SubscriptionStatus.ACTIVE

def test_webhook_duplicate_idempotency(client: TestClient, db: Session):
    # Assume the same setup as above already hit SUCCESS
    # Just mock an existing payment directly
    payment_id = uuid4()
    invoice_id = uuid4()
    
    # Needs valid org, skip for brevity as we just want idempotency response check
    # The endpoint will short circuit at idempotency check
    db.add(Payment(
        id=payment_id,
        invoice_id=invoice_id,
        amount=100.0,
        gateway=PaymentGateway.STRIPE,
        status=PaymentStatus.SUCCESS
    ))
    db.commit()

    webhook_payload = {
        "payment_id": str(payment_id),
        "gateway_payment_id": "pay_xyz123",
        "amount": 100.0,
        "status": "SUCCESS"
    }
    
    resp = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Already processed"

def test_webhook_payment_failure(client: TestClient, db: Session, test_organization):
    invoice_id = uuid4()
    invoice = Invoice(
        id=invoice_id,
        organization_id=test_organization.id,
        amount=100.0,
        due_date="2027-01-01 00:00:00",
        status=InvoiceStatus.PENDING
    )
    db.add(invoice)
    db.flush()

    payment_id = uuid4()
    payment = Payment(
        id=payment_id,
        invoice_id=invoice_id,
        amount=100.0,
        gateway=PaymentGateway.STRIPE,
        status=PaymentStatus.INITIATED
    )
    db.add(payment)
    db.commit()

    webhook_payload = {
        "payment_id": str(payment_id),
        "gateway_payment_id": "pay_xyz_failed",
        "amount": 100.0,
        "status": "FAILED"
    }

    resp = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert resp.status_code == 200

    db.refresh(invoice)
    db.refresh(payment)
    assert payment.status == PaymentStatus.FAILED
    assert invoice.status == InvoiceStatus.FAILED

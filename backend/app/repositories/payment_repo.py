import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus

class PaymentRepository:
    """Repository for managing Payments and Invoices"""

    # --- Invoice Methods ---

    @staticmethod
    def create_invoice(db: Session, organization_id: int, amount: float, due_date, subscription_id: Optional[int] = None) -> Invoice:
        tax_amount = round(float(amount) * 0.18, 2)
        final_amount = round(float(amount) + tax_amount, 2)
        
        invoice = Invoice(
            organization_id=organization_id,
            subscription_id=subscription_id,
            amount=amount,
            tax_amount=tax_amount,
            discount_amount=0.0,
            final_amount=final_amount,
            due_date=due_date,
            status=InvoiceStatus.PENDING
        )
        db.add(invoice)
        db.flush()
        return invoice

    @staticmethod
    def get_invoice_by_id(db: Session, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()

    @staticmethod
    def get_invoices_by_org(db: Session, organization_id: int, skip: int = 0, limit: int = 50) -> List[Invoice]:
        return db.query(Invoice).filter(Invoice.organization_id == organization_id).order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_all_invoices(db: Session, skip: int = 0, limit: int = 50) -> List[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

    # --- Payment Methods ---

    @staticmethod
    def create_payment(db: Session, invoice_id: uuid.UUID, amount: float, gateway: str) -> Payment:
        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            gateway=gateway,
            status=PaymentStatus.INITIATED
        )
        db.add(payment)
        db.flush()
        return payment

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: uuid.UUID) -> Optional[Payment]:
        return db.query(Payment).filter(Payment.id == payment_id).first()

    @staticmethod
    def get_payment_by_id_for_update(db: Session, payment_id: uuid.UUID) -> Optional[Payment]:
        return db.query(Payment).filter(Payment.id == payment_id).with_for_update().first()

    @staticmethod
    def get_payment_by_gateway_id(db: Session, gateway_payment_id: str) -> Optional[Payment]:
        return db.query(Payment).filter(Payment.gateway_payment_id == gateway_payment_id).first()

    @staticmethod
    def get_payments_by_invoice(db: Session, invoice_id: uuid.UUID) -> List[Payment]:
        return db.query(Payment).filter(Payment.invoice_id == invoice_id).order_by(Payment.created_at.desc()).all()

    @staticmethod
    def create_payment_event(db: Session, payment_id: Optional[uuid.UUID], signature: Optional[str], status: str, payload: dict):
        from app.models.payment import PaymentEvent
        event = PaymentEvent(
            payment_id=payment_id,
            gateway_signature=signature,
            processing_status=status,
            raw_payload=payload
        )
        db.add(event)
        db.flush()
        return event

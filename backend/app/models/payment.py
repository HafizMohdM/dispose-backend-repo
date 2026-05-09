import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin

class PaymentGateway(str, enum.Enum):
    STRIPE = "STRIPE"
    RAZORPAY = "RAZORPAY"

class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True)
    
    gateway = Column(Enum(PaymentGateway), nullable=False)
    gateway_payment_id = Column(String(255), nullable=True, unique=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.INITIATED, nullable=False, index=True)
    
    # Store the raw webhook response for auditing/debugging
    raw_response = Column(JSONB, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")

    __table_args__ = (
        Index('ix_one_success_payment', 'invoice_id', unique=True, postgresql_where=(status == 'SUCCESS')),
    )

class PaymentEvent(Base, TimestampMixin):
    """
    Enterprise audit trail for every single webhook or state change 
    associated with a Payment transaction payload.
    """
    __tablename__ = "payment_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, index=True)
    
    gateway_signature = Column(String(255), nullable=True)
    processing_status = Column(String(50), nullable=False) # e.g 'PROCESSED', 'IGNORED_DUPLICATE', 'SIGNATURE_FAILED'
    raw_payload = Column(JSONB, nullable=False)
    
    # Relationships
    payment = relationship("Payment")

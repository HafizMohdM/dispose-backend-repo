import uuid
import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.models.base import Base, TimestampMixin

class InvoiceStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Using Integer because organizations.id and subscriptions.id are Integer in the DB
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False) # Base amount
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    final_amount = Column(Numeric(10, 2), nullable=False) # Actual amount to be paid
    
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False, index=True)
    
    due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization")
    subscription = relationship("Subscription")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

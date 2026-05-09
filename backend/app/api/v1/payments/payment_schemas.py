import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentStatus, PaymentGateway

# --- INVOICE SCHEMAS ---

class InvoiceResponse(BaseModel):
    id: uuid.UUID
    organization_id: int
    subscription_id: Optional[int] = None
    amount: float
    currency: str
    status: InvoiceStatus
    due_date: datetime
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaginatedInvoiceResponse(BaseModel):
    total: int
    data: List[InvoiceResponse]

# --- PAYMENT SCHEMAS ---

class PaymentInitiateRequest(BaseModel):
    invoice_id: uuid.UUID
    gateway: PaymentGateway

class PaymentRetryRequest(BaseModel):
    gateway: PaymentGateway

class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    gateway: PaymentGateway
    amount: float
    status: PaymentStatus
    session_data: Dict[str, Any] = Field(description="Mock gateway session URL or data")

class PaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    gateway: PaymentGateway
    gateway_payment_id: Optional[str] = None
    amount: float
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True

class WebhookRequest(BaseModel):
    payment_id: uuid.UUID
    gateway_payment_id: str
    amount: float
    status: PaymentStatus
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

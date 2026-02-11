from .base import Base

class Payment(Base):
    __tablename__ = "payments"
    pass

class PaymentWebhook(Base):
    __tablename__ = "payment_webhooks"
    pass

class Invoice(Base):
    __tablename__ = "invoices"
    pass

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from app.models.base import Base
from datetime import datetime


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

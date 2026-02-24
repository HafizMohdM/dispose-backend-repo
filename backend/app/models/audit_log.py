from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from app.models.base import Base
from datetime import datetime


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, default="role")
    entity_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

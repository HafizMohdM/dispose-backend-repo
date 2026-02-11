from .base import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"
    pass

class AuditLog(Base):
    __tablename__ = "audit_logs"
    pass

class ApiLog(Base):
    __tablename__ = "api_logs"
    pass

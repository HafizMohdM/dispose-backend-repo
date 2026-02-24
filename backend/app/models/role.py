from app.models.base import Base, TimestampMixin
from sqlalchemy import Column, Integer, String, Boolean

from sqlalchemy.orm import relationship

class Role(Base,TimestampMixin):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

class Permission(Base,TimestampMixin):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=False)


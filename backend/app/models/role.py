from app.models.base import Base, TimestampMixin
from sqlalchemy import Column, Integer, String

class Role(Base,TimestampMixin):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

class Permission(Base,TimestampMixin):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=False)


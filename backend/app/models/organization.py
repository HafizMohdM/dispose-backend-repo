from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base, TimestampMixin

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    category_id = Column(Integer, ForeignKey("organization_categories.id"), nullable=True)

class OrganizationCategory(Base, TimestampMixin):
    __tablename__ = "organization_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

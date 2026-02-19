from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)

    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    category_id = Column(Integer, ForeignKey("organization_categories.id"), nullable=False)

    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    contact_number = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)

    status = Column(String(50), default="PENDING")  # PENDING, ACTIVE, REJECTED
    is_active = Column(Boolean, default=True)

    # Relationships
    category = relationship("OrganizationCategory", backref="organizations")

class OrganizationCategory(Base, TimestampMixin):
    __tablename__ = "organization_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

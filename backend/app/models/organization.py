from .base import Base

class Organization(Base):
    __tablename__ = "organizations"
    pass

class OrganizationCategory(Base):
    __tablename__ = "organization_categories"
    pass

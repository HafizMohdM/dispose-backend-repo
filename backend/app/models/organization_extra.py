from .base import Base

class OrganizationProfile(Base):
    __tablename__ = "organization_profiles"
    pass

class OrganizationUser(Base):
    __tablename__ = "organization_users"
    pass

class OrganizationCompliance(Base):
    __tablename__ = "organization_compliance"
    pass

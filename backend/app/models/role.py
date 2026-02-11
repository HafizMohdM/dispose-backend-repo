from .base import Base

class Role(Base):
    __tablename__ = "roles"
    pass

class Permission(Base):
    __tablename__ = "permissions"
    pass

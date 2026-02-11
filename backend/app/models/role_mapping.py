from .base import Base

class RolePermission(Base):
    __tablename__ = "role_permissions"
    pass

class UserRole(Base):
    __tablename__ = "user_roles"
    pass

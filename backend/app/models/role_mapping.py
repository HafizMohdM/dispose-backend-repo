from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.models.base import Base, TimestampMixin

class RolePermission(Base,TimestampMixin):
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    

class UserRole(Base,TimestampMixin):
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id","org_id", name="uq_user_role"),
    )


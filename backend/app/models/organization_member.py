import enum
import uuid
from sqlalchemy import Column, Integer, ForeignKey, Enum, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from app.models.base import Base, TimestampMixin

class MembershipStatus(str, enum.Enum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"

class OrganizationMember(Base, TimestampMixin):
    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    status = Column(Enum(MembershipStatus), default=MembershipStatus.ACTIVE, nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),
    )

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role")
    inviter = relationship("User", foreign_keys=[invited_by])

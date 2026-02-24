from sqlalchemy import Column, Integer, String,ForeignKey, Boolean,DateTime, Text
from app.models.base import Base, TimestampMixin
from sqlalchemy.orm import relationship


class User(Base,TimestampMixin):
    __tablename__ = "users"
    id=Column(Integer,primary_key=True,index=True)
    mobile=Column(String(15),unique=True,nullable=False,index=True)
    email=Column(String(255),unique=True,nullable=True)
    is_active=Column(Boolean,default=True,nullable=False)

    # Auth hardening fields
    last_login_at = Column(DateTime, nullable=True)
    token_version = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base,TimestampMixin):
    __tablename__ = "user_sessions"

    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    token=Column(String(512),unique=True,nullable=False)
    refresh_token=Column(String(512),unique=True,nullable=True)
    expires_at=Column(DateTime,nullable=False)
    failed_attempts=Column(Integer,default=0,nullable=False)
    ip_address=Column(String(45),nullable=True)
    device_name=Column(String(255),nullable=True)
    user_agent=Column(Text,nullable=True)

    user=relationship("User")


from sqlalchemy import Column, Integer, String,ForeignKey, Boolean,DateTime
from app.models.base import Base, TimestampMixin
from sqlalchemy.orm import relationship


class User(Base,TimestampMixin):
    __tablename__ = "users"
    id=Column(Integer,primary_key=True,index=True)
    mobile=Column(String(15),unique=True,nullable=False,index=True)
    email=Column(String(255),unique=True,nullable=True)
    is_active=Column(Boolean,default=True,nullable=False)


class UserSession(Base,TimestampMixin):
    __tablename__ = "user_sessions"

    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    token=Column(String(512),unique=True,nullable=False)
    expires_at=Column(DateTime,nullable=False)

    user=relationship("User")


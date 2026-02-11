from .base import Base

class User(Base):
    __tablename__ = "users"
    pass

class UserSession(Base):
    __tablename__ = "user_sessions"
    pass

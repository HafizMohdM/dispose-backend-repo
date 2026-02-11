from .base import Base

class Notification(Base):
    __tablename__ = "notifications"
    pass

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    pass

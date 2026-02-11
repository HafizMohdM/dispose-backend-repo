from .base import Base

class Complaint(Base):
    __tablename__ = "complaints"
    pass

class ComplaintComment(Base):
    __tablename__ = "complaint_comments"
    pass

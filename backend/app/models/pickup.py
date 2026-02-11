from .base import Base

class Pickup(Base):
    __tablename__ = "pickups"
    pass

class PickupSchedule(Base):
    __tablename__ = "pickup_schedule"
    pass

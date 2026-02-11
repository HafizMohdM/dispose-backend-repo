from .base import Base

class Driver(Base):
    __tablename__ = "drivers"
    pass

class DriverLocation(Base):
    __tablename__ = "driver_locations"
    pass

class DriverAvailability(Base):
    __tablename__ = "driver_availability"
    pass

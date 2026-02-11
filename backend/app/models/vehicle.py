from .base import Base

class Vehicle(Base):
    __tablename__ = "vehicles"
    pass

class DriverVehicleMap(Base):
    __tablename__ = "driver_vehicle_map"
    pass

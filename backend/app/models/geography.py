from .base import Base

class Country(Base):
    __tablename__ = "countries"
    pass

class State(Base):
    __tablename__ = "states"
    pass

class City(Base):
    __tablename__ = "cities"
    pass

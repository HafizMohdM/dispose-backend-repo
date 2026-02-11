from .base import Base

class WasteAggregate(Base):
    __tablename__ = "waste_aggregates"
    pass

class ImpactMetric(Base):
    __tablename__ = "impact_metrics"
    pass

class CityImpactSummary(Base):
    __tablename__ = "city_impact_summary"
    pass

from pydantic import BaseModel
from uuid import UUID


class TopDriverResponse(BaseModel):

    id: UUID
    name: str
    completed_pickups: int


class DriverUtilizationResponse(BaseModel):

    id: UUID
    name: str
    total_assignments: int
    completed_pickups: int


class DriverPerformanceResponse(BaseModel):

    id: UUID
    name: str
    total_assignments: int
    completed_pickups: int
    cancelled_pickups: int
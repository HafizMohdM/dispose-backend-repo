import uuid
from sqlalchemy import Column, String, DateTime, Enum, Float, Integer, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.utils.enums import DriverStatus, DriverAvailabilityStatus
from app.models.base import Base


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    mobile = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)

    license_number = Column(String(100), nullable=True)
    license_expiry = Column(DateTime, nullable=True)

    status = Column(
        Enum(DriverStatus),
        nullable=False,
        default=DriverStatus.ACTIVE,
        index=True,
    )

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DriverLocation(Base):
    __tablename__ = "driver_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class DriverAvailability(Base):
    __tablename__ = "driver_availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(DriverAvailabilityStatus),
        nullable=False,
        default=DriverAvailabilityStatus.OFFLINE,
        index=True,
    )

    is_on_duty = Column(Boolean, default=False, nullable=False)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

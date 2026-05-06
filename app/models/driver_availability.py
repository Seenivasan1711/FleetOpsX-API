import uuid
from datetime import date as date_type
from sqlalchemy import Column, String, Float, Time, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

DRIVER_AVAILABILITY_STATUSES = ("available", "on_break", "off_duty")


class DriverAvailability(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_availability"
    __table_args__ = (
        UniqueConstraint("driver_id", "date", name="uq_driver_availability_driver_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    shift_start = Column(Time, nullable=True)
    shift_end = Column(Time, nullable=True)
    # available | on_break | off_duty
    status = Column(String(20), nullable=False, default="available")
    hours_worked_today = Column(Float, nullable=False, default=0.0)

    driver = relationship("Driver", backref="availability_records")

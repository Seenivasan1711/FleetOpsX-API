import uuid
from sqlalchemy import Column, Date, Time, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin


class DriverShift(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_shifts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    shift_date = Column(Date, nullable=False, index=True)
    shift_start = Column(Time, nullable=False)
    shift_end = Column(Time, nullable=False)
    status = Column(String(50), nullable=False, default="WORKING")
    # WORKING | LEAVE | SICK | HOLIDAY
    is_available = Column(Boolean, default=True)

    driver = relationship("Driver", back_populates="shifts")

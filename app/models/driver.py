import uuid
from sqlalchemy import Column, String, Float, Boolean, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin


class Driver(Base, TimestampMixin, TenantMixin):
    __tablename__ = "drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    license_number = Column(String(100), nullable=True)
    license_class = Column(String(50), nullable=True)
    # LMV | HMV | TRANS
    default_shift_start = Column(Time, nullable=True)
    default_shift_end = Column(Time, nullable=True)
    home_depot_id = Column(
        UUID(as_uuid=True), ForeignKey("depots.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    is_active = Column(Boolean, default=True)

    home_depot = relationship("Depot", back_populates="drivers")
    shifts = relationship("DriverShift", back_populates="driver", cascade="all, delete-orphan")

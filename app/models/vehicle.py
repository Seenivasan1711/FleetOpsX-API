import uuid
from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin


class Vehicle(Base, TimestampMixin, TenantMixin):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_number = Column(String(50), nullable=False, index=True)
    vehicle_type = Column(String(50), nullable=False, default="VAN")
    # BIKE | AUTO | VAN | TRUCK_SMALL | TRUCK_LARGE
    capacity_kg = Column(Float, nullable=True)
    capacity_volume_liters = Column(Float, nullable=True)
    capacity_units = Column(Integer, nullable=True)
    is_refrigerated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    home_depot_id = Column(
        UUID(as_uuid=True), ForeignKey("depots.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    home_depot = relationship("Depot", back_populates="vehicles")

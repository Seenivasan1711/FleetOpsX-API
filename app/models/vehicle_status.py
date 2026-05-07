import uuid
from sqlalchemy import Column, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

VEHICLE_STATUS_VALUES = ("available", "in_use", "maintenance")


class VehicleStatus(Base, TimestampMixin, TenantMixin):
    __tablename__ = "vehicle_status"
    __table_args__ = (
        UniqueConstraint("vehicle_id", name="uq_vehicle_status_vehicle"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    current_mileage = Column(Float, nullable=True)
    fuel_level_pct = Column(Float, nullable=True)
    # available | in_use | maintenance
    status = Column(String(20), nullable=False, default="available")

    vehicle = relationship("Vehicle", backref="status_record")

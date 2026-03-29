import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin


class DriverLocationPing(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_location_pings"
    __table_args__ = (
        Index("ix_dlp_driver_recorded", "driver_id", "recorded_at"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id   = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    vehicle_id  = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    latitude    = Column(Float, nullable=False)
    longitude   = Column(Float, nullable=False)
    accuracy_m  = Column(Float, nullable=True)
    speed_kmh   = Column(Float, nullable=True)
    heading_deg = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

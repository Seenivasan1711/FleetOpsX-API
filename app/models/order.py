import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, Time, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin


class Order(Base, TimestampMixin, TenantMixin):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref = Column(String(255), nullable=True, index=True)
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    pickup_address = Column(String(500), nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    delivery_address = Column(String(500), nullable=False)
    delivery_latitude = Column(Float, nullable=True)
    delivery_longitude = Column(Float, nullable=True)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    time_window_start = Column(Time, nullable=True)
    time_window_end = Column(Time, nullable=True)
    weight_kg = Column(Float, nullable=True)
    volume_liters = Column(Float, nullable=True)
    quantity_units = Column(Integer, nullable=True)
    requires_refrigeration = Column(Boolean, default=False)
    priority = Column(String(20), nullable=False, default="NORMAL")
    # LOW | NORMAL | HIGH | CRITICAL
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    # PENDING | ASSIGNED | IN_TRANSIT | DELIVERED | FAILED | CANCELLED
    notes = Column(Text, nullable=True)
    assigned_driver_id = Column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    assigned_vehicle_id = Column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    customer = relationship("Customer", back_populates="orders")
    assigned_driver = relationship("Driver", foreign_keys=[assigned_driver_id])
    assigned_vehicle = relationship("Vehicle", foreign_keys=[assigned_vehicle_id])
    route_stop = relationship("RouteStop", back_populates="order", uselist=False)

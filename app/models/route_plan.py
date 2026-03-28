import uuid
from sqlalchemy import Column, Date, String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin


class RoutePlan(Base, TimestampMixin, TenantMixin):
    __tablename__ = "route_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="DRAFT")
    # DRAFT | PUBLISHED | IN_PROGRESS | COMPLETED
    total_orders = Column(Integer, default=0)
    assigned_orders = Column(Integer, default=0)
    total_routes = Column(Integer, default=0)
    planner_version = Column(String(50), nullable=True, default="rule_based_v1")

    routes = relationship("Route", back_populates="plan", cascade="all, delete-orphan")


class Route(Base, TimestampMixin, TenantMixin):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("route_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="PLANNED")
    # PLANNED | STARTED | COMPLETED | CANCELLED
    total_stops = Column(Integer, default=0)
    estimated_duration_minutes = Column(Float, nullable=True)
    estimated_distance_km = Column(Float, nullable=True)

    plan = relationship("RoutePlan", back_populates="routes")
    driver = relationship("Driver")
    vehicle = relationship("Vehicle")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence")


class RouteStop(Base, TimestampMixin, TenantMixin):
    __tablename__ = "route_stops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    # PENDING | ARRIVED | DELIVERED | FAILED | SKIPPED
    estimated_arrival = Column(String(50), nullable=True)
    actual_arrival = Column(String(50), nullable=True)

    route = relationship("Route", back_populates="stops")
    order = relationship("Order", back_populates="route_stop")


class DeliveryEvent(Base, TimestampMixin, TenantMixin):
    __tablename__ = "delivery_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_stop_id = Column(UUID(as_uuid=True), ForeignKey("route_stops.id", ondelete="CASCADE"), nullable=True, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # ASSIGNED | STARTED | ARRIVED | DELIVERED | FAILED | DELAYED | CANCELLED | NOTE
    description = Column(String(500), nullable=True)
    recorded_by = Column(String(100), nullable=True)
    # "driver" | "system" | "dispatcher" | user_id

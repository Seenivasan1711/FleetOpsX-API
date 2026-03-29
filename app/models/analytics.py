"""
Analytics models — P3-E1

DeliveryAnalytics: one row per completed order delivery (denormalized fact table)
DriverPerformanceScore: one row per driver per date (daily aggregate)
"""
import uuid
from sqlalchemy import Column, Date, Integer, Float, Boolean, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin


class DeliveryAnalytics(Base, TimestampMixin, TenantMixin):
    __tablename__ = "delivery_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    route_plan_id = Column(UUID(as_uuid=True), ForeignKey("route_plans.id", ondelete="SET NULL"), nullable=True, index=True)

    delivery_date = Column(Date, nullable=False, index=True)   # plan_date
    day_of_week = Column(Integer, nullable=False)               # 0=Mon … 6=Sun
    hour_of_day = Column(Integer, nullable=True)                # hour delivery completed

    zone = Column(String(100), nullable=True, index=True)       # first token of delivery_address
    planned_eta = Column(String(8), nullable=True)              # order.time_window_end as HH:MM:SS
    actual_arrival = Column(DateTime, nullable=True)            # from DeliveryEvent(DELIVERED)
    delay_minutes = Column(Integer, nullable=True)              # max(0, actual - planned) in minutes
    was_on_time = Column(Boolean, nullable=True)                # True if delay_minutes == 0 or NULL window

    priority = Column(String(20), nullable=False, default="NORMAL")


class DriverPerformanceScore(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_performance_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    score_date = Column(Date, nullable=False, index=True)       # upsert key together with driver_id

    total_deliveries = Column(Integer, default=0)
    on_time_count = Column(Integer, default=0)
    on_time_rate = Column(Float, nullable=True)                 # on_time_count / total_deliveries
    avg_delay_min = Column(Float, nullable=True)                # average delay where delay > 0
    total_delay_min = Column(Integer, default=0)

from uuid import uuid4
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base, TenantMixin


class PlanHistory(TenantMixin, Base):
    __tablename__ = "plan_history"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_date      = Column(Date, nullable=False, index=True)
    scenario_type  = Column(String(50), nullable=True)
    source         = Column(String(50), nullable=False, default="manual")  # ai_scenario | or_tools | manual
    total_orders   = Column(Integer, nullable=True)
    total_routes   = Column(Integer, nullable=True)
    coverage_pct   = Column(Float, nullable=True)
    est_fuel_cost_inr = Column(Float, nullable=True)
    total_time_min = Column(Integer, nullable=True)
    ai_confidence  = Column(Float, nullable=True)
    created_by     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    notes = relationship("PlanNote", back_populates="plan_history", cascade="all, delete-orphan", order_by="PlanNote.created_at")


class PlanNote(TenantMixin, Base):
    __tablename__ = "plan_notes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_history_id = Column(UUID(as_uuid=True), ForeignKey("plan_history.id", ondelete="CASCADE"), nullable=False, index=True)
    note            = Column(Text, nullable=False)
    rating          = Column(Integer, nullable=True)  # 1-5
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    plan_history = relationship("PlanHistory", back_populates="notes")

"""ScenarioRun + ScenarioResult models — P4-E5."""
import uuid
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, TenantMixin


class ScenarioRun(Base, TimestampMixin, TenantMixin):
    __tablename__ = "scenario_runs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(200), nullable=False)
    scenario_type   = Column(String(50),  nullable=False)   # new_depot | ev_fleet_mix | driver_count_change | demand_surge
    parameters      = Column(JSON, nullable=False, default=dict)
    horizon_start   = Column(Date, nullable=False)
    horizon_days    = Column(Integer, nullable=False, default=7)
    status          = Column(String(20), nullable=False, default="QUEUED")  # QUEUED | RUNNING | COMPLETED | FAILED
    baseline_kpis   = Column(JSON, nullable=True)
    created_by      = Column(String(100), nullable=False)
    completed_at    = Column(DateTime(timezone=True), nullable=True)

    results = relationship("ScenarioResult", back_populates="scenario_run",
                           cascade="all, delete-orphan", lazy="dynamic")


class ScenarioResult(Base, TimestampMixin, TenantMixin):
    __tablename__ = "scenario_results"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_run_id    = Column(UUID(as_uuid=True),
                                 ForeignKey("scenario_runs.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    plan_date          = Column(Date, nullable=False)
    total_routes       = Column(Integer, default=0)
    assigned_orders    = Column(Integer, default=0)
    on_time_rate       = Column(Float, default=0.0)
    avg_delay_min      = Column(Float, default=0.0)
    total_distance_km  = Column(Float, default=0.0)
    fleet_utilization  = Column(Float, default=0.0)
    kpi_delta          = Column(JSON, nullable=True)   # diff vs baseline per KPI

    scenario_run = relationship("ScenarioRun", back_populates="results")

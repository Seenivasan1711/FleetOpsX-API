"""
PlanningSession model — AI-1 E3.

Lifecycle: OPEN → LOCKED (auto at cutoff_at) | COMPLETED (dispatcher confirms) | EXPIRED (cutoff passed with no confirm).
Each session owns N versioned RoutePlan rows (session_id FK on route_plans).
active_plan_id always points to the latest AI-generated version.
"""
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, TenantMixin


class PlanningSession(Base, TimestampMixin, TenantMixin):
    __tablename__ = "planning_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="OPEN")
    # OPEN | LOCKED | COMPLETED | EXPIRED

    # Timestamp when the session is auto-locked (from TenantConfig planning_cutoff_time)
    cutoff_at = Column(DateTime(timezone=True), nullable=False)

    # Latest active plan version for this session (FK added via use_alter to break circular dep)
    active_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("route_plans.id", use_alter=True, name="fk_planning_sessions_active_plan", ondelete="SET NULL"),
        nullable=True,
    )

    # User who opened the session
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Full accumulated hint list (all rounds); passed to runner as session_hints
    accumulated_hints = Column(JSONB, nullable=True, default=list)

    # All versioned plans for this session (populated via route_plans.session_id FK)
    plans = relationship(
        "RoutePlan",
        foreign_keys="RoutePlan.session_id",
        back_populates="session",
        order_by="RoutePlan.version_number",
    )

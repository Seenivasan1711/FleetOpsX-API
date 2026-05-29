"""
PlanningLearning model — AI-1 E4.

Detected planning patterns written by LearningUpdaterAgent (Phase 3).
Status PENDING until a dispatcher approves/rejects.
Only APPROVED patterns are loaded into AgentContext.learning_patterns.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TimestampMixin, TenantMixin


class PlanningLearning(Base, TimestampMixin, TenantMixin):
    __tablename__ = "planning_learning"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Short machine tag: "high_drop_rate" | "zone_concentration" | "repeated_replan" | "constraint_conflict"
    pattern_type = Column(String(60), nullable=False, index=True)

    # Human-readable description shown in the UI
    pattern_text = Column(Text, nullable=False)

    # Data that triggered this observation (serialised plan + context snapshot)
    trigger_conditions = Column(JSONB, nullable=True)

    # Number of times the same pattern_type has been observed since last reset
    times_observed = Column(Integer, nullable=False, default=1)

    # PENDING_APPROVAL | APPROVED | REJECTED
    status = Column(String(20), nullable=False, default="PENDING_APPROVAL", index=True)

    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime, nullable=True)

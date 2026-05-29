"""
OverrideLog model — AI-1 E8.

Audits every dispatcher-driven plan mutation applied via the planning chat agent.
"""
import uuid

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base, TimestampMixin, TenantMixin


class OverrideLog(Base, TimestampMixin, TenantMixin):
    __tablename__ = "override_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("planning_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("route_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # MOVE_ORDER | FLAG_OVERTIME | MANUAL_ADJUST
    override_type = Column(String(60), nullable=False, index=True)

    applied_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reason_text = Column(Text, nullable=False, default="")
    payload = Column(JSONB, nullable=True)

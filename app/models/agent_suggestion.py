"""
AgentSuggestion model — P3-E2

One row per proactive suggestion created by the Monitor Agent.
Dispatchers can Accept or Dismiss each suggestion via the UI.
"""
import uuid
from sqlalchemy import Column, Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.models.base import Base, TimestampMixin, TenantMixin


class AgentSuggestion(Base, TimestampMixin, TenantMixin):
    __tablename__ = "agent_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    plan_date = Column(Date, nullable=False, index=True)
    suggestion_type = Column(String(50), nullable=False)
    # REPLAN_DRIVER | EARLY_SLA_WARNING | DEMAND_WARNING | RESCHEDULE_STOP

    status = Column(String(20), nullable=False, default="PENDING", index=True)
    # PENDING | ACCEPTED | DISMISSED

    priority = Column(String(20), nullable=False, default="NORMAL")
    # HIGH | NORMAL

    title = Column(String(200), nullable=False)
    detail = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)       # { driver_id, stop_id, order_ids, ... }
    expires_at = Column(DateTime, nullable=True)
    acted_by = Column(String(100), nullable=True)  # user who accepted/dismissed

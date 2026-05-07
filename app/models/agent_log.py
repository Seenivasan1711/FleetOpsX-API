import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin


class AgentLog(Base, TimestampMixin, TenantMixin):
    __tablename__ = "agent_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id      = Column(UUID(as_uuid=True), ForeignKey("route_plans.id", ondelete="SET NULL"), nullable=True)
    step         = Column(String(100))          # "fetch_context" | "call_optimizer" | "explain"
    role         = Column(String(20))           # "agent" | "tool" | "llm"
    content      = Column(Text)                 # message / reasoning / tool result
    llm_provider = Column(String(50), nullable=True)  # which provider was used

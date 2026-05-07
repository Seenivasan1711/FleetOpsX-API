"""AuditLogEntry — append-only immutable audit trail (P4-E4)."""
import uuid
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.models.base import Base, TenantMixin


class AuditLogEntry(Base, TenantMixin):
    """Immutable audit record — no UPDATE or DELETE ever applied.

    No TimestampMixin: created_at is set once by the DB and never touched.
    """
    __tablename__ = "audit_log_entries"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor_email   = Column(String(200), nullable=False)
    actor_role    = Column(String(50), nullable=False)
    action        = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id   = Column(UUID(as_uuid=True), nullable=True)
    before_state  = Column(JSON, nullable=True)
    after_state   = Column(JSON, nullable=True)
    ip_address    = Column(String(50), nullable=True)
    user_agent    = Column(String(200), nullable=True)
    ai_context    = Column(JSON, nullable=True)

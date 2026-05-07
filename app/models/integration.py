import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin


class WebhookRegistration(Base, TimestampMixin, TenantMixin):
    __tablename__ = "webhook_registrations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url         = Column(String(500), nullable=False)
    event_types = Column(JSON, nullable=False)       # list[str]: ["order.delivered", ...]
    secret      = Column(String(500), nullable=True) # encrypted HMAC signing secret
    is_active   = Column(Boolean, default=True, nullable=False)
    last_error  = Column(Text, nullable=True)


class IntegrationLog(Base, TimestampMixin, TenantMixin):
    __tablename__ = "integration_logs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_order_id = Column(String(200), nullable=False)   # idempotency key
    source_system    = Column(String(100), nullable=False)   # "SAP" | "Shopify" | "generic"
    raw_payload      = Column(JSON, nullable=True)
    normalized       = Column(Boolean, default=False, nullable=False)
    order_id         = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"),
                               nullable=True)
    error_message    = Column(Text, nullable=True)

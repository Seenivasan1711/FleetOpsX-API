import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class AiProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    provider_name = Column(String(50), nullable=False)   # claude | openai | gemini
    model_id      = Column(String(100), nullable=False)  # claude-sonnet-4-6 | gpt-4o | gemini-pro
    api_key_enc   = Column(String(500), nullable=True)   # Fernet encrypted; NULL = use env var
    task_type     = Column(String(30), nullable=False)   # planning | chat | analysis | all
    is_active     = Column(Boolean, default=True, nullable=False)
    is_platform_default = Column(Boolean, default=False, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_name", "task_type", name="uq_ai_provider_tenant_task"),
    )

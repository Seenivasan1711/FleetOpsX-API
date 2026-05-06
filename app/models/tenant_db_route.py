import uuid
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class TenantDbRoute(Base, TimestampMixin):
    __tablename__ = "tenant_db_routes"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id         = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
                               unique=True, nullable=False, index=True)
    connection_string = Column(String(500), nullable=False)   # encrypted at rest
    region            = Column(String(100), nullable=True)
    is_active         = Column(Boolean, default=True, nullable=False)
    max_pool_size     = Column(Integer, default=10, nullable=False)

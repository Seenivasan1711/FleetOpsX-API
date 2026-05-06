"""RbacRole — fine-grained permission sets per role (P4-E4)."""
import uuid
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.models.base import Base, TimestampMixin, TenantMixin


class RbacRole(Base, TimestampMixin, TenantMixin):
    __tablename__ = "rbac_roles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False)
    permissions = Column(ARRAY(String), nullable=False, default=list)
    is_system   = Column(Boolean, default=False, nullable=False)

import uuid
from sqlalchemy import Column, ForeignKey, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin


class User(Base, TimestampMixin, TenantMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Superadmin users have no tenant — nullable overrides TenantMixin's NOT NULL
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    email = Column(String(255), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="dispatcher")
    # Roles: superadmin | admin | dispatcher | driver | readonly | packaging_team
    is_active = Column(Boolean, default=True)

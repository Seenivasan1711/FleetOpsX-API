import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin

_OFFER_STATUS   = "OPEN"       # OPEN | MATCHED | CANCELLED | EXPIRED
_REQUEST_STATUS = "OPEN"       # OPEN | MATCHED | CANCELLED | EXPIRED
_MATCH_STATUS   = "PENDING_ACCEPTANCE"  # PENDING_ACCEPTANCE | ACCEPTED | REJECTED | COMPLETED


class CapacityOffer(Base, TimestampMixin, TenantMixin):
    __tablename__ = "capacity_offers"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_date    = Column(Date, nullable=False)
    driver_count  = Column(Integer, nullable=False)
    vehicle_type  = Column(String(50), nullable=True)   # VAN | TRUCK | BIKE | None = any
    zone          = Column(String(100), nullable=False)
    rate_per_stop = Column(Float, nullable=True)         # display only
    status        = Column(String(20), nullable=False, default="OPEN")
    expires_at    = Column(DateTime, nullable=False)


class CapacityRequest(Base, TimestampMixin, TenantMixin):
    __tablename__ = "capacity_requests"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_date = Column(Date, nullable=False)
    order_count  = Column(Integer, nullable=False)
    zone         = Column(String(100), nullable=False)
    priority     = Column(String(20), nullable=False, default="NORMAL")  # HIGH | NORMAL
    status       = Column(String(20), nullable=False, default="OPEN")
    expires_at   = Column(DateTime, nullable=False)


class CapacityMatch(Base, TimestampMixin):
    """Cross-tenant record — no TenantMixin."""
    __tablename__ = "capacity_matches"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id              = Column(UUID(as_uuid=True), ForeignKey("capacity_offers.id",   ondelete="CASCADE"), nullable=False)
    request_id            = Column(UUID(as_uuid=True), ForeignKey("capacity_requests.id", ondelete="CASCADE"), nullable=False)
    offering_tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id"),          nullable=False)
    requesting_tenant_id  = Column(UUID(as_uuid=True), ForeignKey("tenants.id"),          nullable=False)
    matched_orders        = Column(Integer, nullable=False, default=0)
    status                = Column(String(20), nullable=False, default="PENDING_ACCEPTANCE")
    settled_at            = Column(DateTime, nullable=True)

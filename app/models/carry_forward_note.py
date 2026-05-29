"""
CarryForwardNote model — AI-1 E5.

Created by CarryForwardAgent (Phase 3) for every order dropped from a plan.
The runner pre-loads today's PENDING notes before Phase 1 so ConstraintValidator
can reference them.

Status lifecycle:
  PENDING    — created by CarryForwardAgent, awaiting tomorrow's plan run
  FULFILLED  — order was successfully assigned on to_date's plan
  EXPIRED    — to_date passed without assignment
"""
import uuid

from sqlalchemy import Column, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, TenantMixin


class CarryForwardNote(Base, TimestampMixin, TenantMixin):
    __tablename__ = "carry_forward_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The dropped order
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Date the order was dropped from
    from_date = Column(Date, nullable=False, index=True)

    # Target date for this note (Day+1 or Day+2 from from_date)
    to_date = Column(Date, nullable=False, index=True)

    # Best-match driver for to_date (may be null if no match found)
    suggested_driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Human-readable context injected into ConstraintValidator LLM prompt
    context_note = Column(Text, nullable=False, default="")

    # PENDING | FULFILLED | EXPIRED
    status = Column(String(20), nullable=False, default="PENDING", index=True)

    order = relationship("Order")
    suggested_driver = relationship("Driver")

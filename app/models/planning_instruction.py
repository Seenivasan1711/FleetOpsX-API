"""
PlanningInstruction model — AI-1 E4.

Dispatcher-authored planning rules injected into every planning run.
Active instructions are loaded before Phase 1 and validated in Phase 2
by ConstraintValidatorAgent.
"""
import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, TenantMixin


class PlanningInstruction(Base, TimestampMixin, TenantMixin):
    __tablename__ = "planning_instructions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_text = Column(Text, nullable=False)
    # 1 = highest priority, 5 = lowest; used to order injection into LLM prompt
    priority = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

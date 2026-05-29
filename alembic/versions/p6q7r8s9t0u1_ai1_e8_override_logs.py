"""ai1_e8_override_logs

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-05-24

Creates the override_logs table for auditing planning chat agent mutations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "p6q7r8s9t0u1"
down_revision = "o5p6q7r8s9t0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "override_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("planning_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("route_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("override_type", sa.String(60), nullable=False),
        sa.Column("applied_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason_text", sa.Text, nullable=False, server_default=""),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_override_logs_tenant_id", "override_logs", ["tenant_id"])
    op.create_index("ix_override_logs_session_id", "override_logs", ["session_id"])
    op.create_index("ix_override_logs_plan_id", "override_logs", ["plan_id"])
    op.create_index("ix_override_logs_override_type", "override_logs", ["override_type"])


def downgrade() -> None:
    op.drop_table("override_logs")

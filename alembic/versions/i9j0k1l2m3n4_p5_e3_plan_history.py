"""p5_e3_plan_history

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'i9j0k1l2m3n4'
down_revision = 'h8i9j0k1l2m3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plan_history',
        sa.Column('id',               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',        postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan_date',        sa.Date(), nullable=False),
        sa.Column('scenario_type',    sa.String(50), nullable=True),
        sa.Column('source',           sa.String(50), nullable=False, server_default='manual'),
        sa.Column('total_orders',     sa.Integer(), nullable=True),
        sa.Column('total_routes',     sa.Integer(), nullable=True),
        sa.Column('coverage_pct',     sa.Float(), nullable=True),
        sa.Column('est_fuel_cost_inr', sa.Float(), nullable=True),
        sa.Column('total_time_min',   sa.Integer(), nullable=True),
        sa.Column('ai_confidence',    sa.Float(), nullable=True),
        sa.Column('created_by',       postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at',       sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_plan_history_plan_date', 'plan_history', ['plan_date'])

    op.create_table(
        'plan_notes',
        sa.Column('id',              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',       postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan_history_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_history.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('note',            sa.Text(), nullable=False),
        sa.Column('rating',          sa.Integer(), nullable=True),
        sa.Column('created_by',      postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('plan_notes')
    op.drop_index('ix_plan_history_plan_date', table_name='plan_history')
    op.drop_table('plan_history')

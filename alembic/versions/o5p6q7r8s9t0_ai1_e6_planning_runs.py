"""ai1_e6_planning_runs

Creates the planning_runs table for AI-1 E6 run tracking.
Each run_planning() call writes one row; checkpoints are appended as JSONB.

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'o5p6q7r8s9t0'
down_revision = 'n4o5p6q7r8s9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'planning_runs',
        sa.Column('id',            sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',     sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('session_id',    sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('planning_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('plan_date',     sa.Date(), nullable=False),
        sa.Column('status',        sa.String(30), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('current_phase', sa.Integer(), nullable=True),
        sa.Column('current_agent', sa.String(100), nullable=True),
        sa.Column('checkpoints',   JSONB(), nullable=True),
        sa.Column('error_info',    JSONB(), nullable=True),
        sa.Column('params',        JSONB(), nullable=True),
        sa.Column('started_at',    sa.DateTime(), nullable=True),
        sa.Column('completed_at',  sa.DateTime(), nullable=True),
        sa.Column('created_at',    sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at',    sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_planning_runs_tenant_id',  'planning_runs', ['tenant_id'])
    op.create_index('ix_planning_runs_plan_date',  'planning_runs', ['plan_date'])
    op.create_index('ix_planning_runs_status',     'planning_runs', ['status'])
    op.create_index('ix_planning_runs_session_id', 'planning_runs', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_planning_runs_session_id', table_name='planning_runs')
    op.drop_index('ix_planning_runs_status',     table_name='planning_runs')
    op.drop_index('ix_planning_runs_plan_date',  table_name='planning_runs')
    op.drop_index('ix_planning_runs_tenant_id',  table_name='planning_runs')
    op.drop_table('planning_runs')

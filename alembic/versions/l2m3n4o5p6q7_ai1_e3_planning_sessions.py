"""ai1_e3_planning_sessions

Creates the planning_sessions table and adds iterative-session columns to
route_plans (session_id, version_number, parent_plan_id, round_hints).

The circular FK (planning_sessions.active_plan_id → route_plans.id) is
added as a separate ALTER TABLE after both tables are in their final shape.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'l2m3n4o5p6q7'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create planning_sessions (active_plan_id FK added in step 3 to break circular dep)
    op.create_table(
        'planning_sessions',
        sa.Column('id',         sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',  sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan_date',  sa.Date(), nullable=False),
        sa.Column('status',     sa.String(20), nullable=False, server_default='OPEN'),
        sa.Column('cutoff_at',  sa.DateTime(timezone=True), nullable=False),
        sa.Column('active_plan_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('accumulated_hints', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_planning_sessions_plan_date', 'planning_sessions', ['plan_date'])
    op.create_index('ix_planning_sessions_tenant_id', 'planning_sessions', ['tenant_id'])

    # 2. Add session versioning columns to route_plans
    op.add_column('route_plans', sa.Column('session_id',
        sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('route_plans', sa.Column('version_number', sa.Integer(), nullable=True))
    op.add_column('route_plans', sa.Column('parent_plan_id',
        sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('route_plans', sa.Column('round_hints', JSONB(), nullable=True))

    op.create_index('ix_route_plans_session_id', 'route_plans', ['session_id'])
    op.create_foreign_key(
        'fk_route_plans_session_id', 'route_plans', 'planning_sessions',
        ['session_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_route_plans_parent_plan_id', 'route_plans', 'route_plans',
        ['parent_plan_id'], ['id'], ondelete='SET NULL',
    )

    # 3. Now add the circular FK from planning_sessions.active_plan_id → route_plans.id
    op.create_foreign_key(
        'fk_planning_sessions_active_plan', 'planning_sessions', 'route_plans',
        ['active_plan_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_planning_sessions_active_plan', 'planning_sessions', type_='foreignkey')

    op.drop_constraint('fk_route_plans_parent_plan_id', 'route_plans', type_='foreignkey')
    op.drop_constraint('fk_route_plans_session_id', 'route_plans', type_='foreignkey')
    op.drop_index('ix_route_plans_session_id', table_name='route_plans')
    op.drop_column('route_plans', 'round_hints')
    op.drop_column('route_plans', 'parent_plan_id')
    op.drop_column('route_plans', 'version_number')
    op.drop_column('route_plans', 'session_id')

    op.drop_index('ix_planning_sessions_tenant_id', table_name='planning_sessions')
    op.drop_index('ix_planning_sessions_plan_date', table_name='planning_sessions')
    op.drop_table('planning_sessions')

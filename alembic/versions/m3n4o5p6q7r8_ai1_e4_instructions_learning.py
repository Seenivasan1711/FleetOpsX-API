"""ai1_e4_instructions_learning

Creates planning_instructions and planning_learning tables for AI-1 E4.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'm3n4o5p6q7r8'
down_revision = 'l2m3n4o5p6q7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'planning_instructions',
        sa.Column('id',         sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',  sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('rule_text',  sa.Text(), nullable=False),
        sa.Column('priority',   sa.Integer(), nullable=False, server_default='3'),
        sa.Column('is_active',  sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_planning_instructions_tenant_id', 'planning_instructions', ['tenant_id'])

    op.create_table(
        'planning_learning',
        sa.Column('id',                  sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',           sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('pattern_type',        sa.String(60), nullable=False),
        sa.Column('pattern_text',        sa.Text(), nullable=False),
        sa.Column('trigger_conditions',  JSONB(), nullable=True),
        sa.Column('times_observed',      sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status',              sa.String(20), nullable=False, server_default='PENDING_APPROVAL'),
        sa.Column('reviewed_by',         sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at',         sa.DateTime(), nullable=True),
        sa.Column('created_at',          sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at',          sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_planning_learning_tenant_id',   'planning_learning', ['tenant_id'])
    op.create_index('ix_planning_learning_status',      'planning_learning', ['status'])
    op.create_index('ix_planning_learning_pattern_type','planning_learning', ['pattern_type'])


def downgrade() -> None:
    op.drop_index('ix_planning_learning_pattern_type', table_name='planning_learning')
    op.drop_index('ix_planning_learning_status',       table_name='planning_learning')
    op.drop_index('ix_planning_learning_tenant_id',    table_name='planning_learning')
    op.drop_table('planning_learning')

    op.drop_index('ix_planning_instructions_tenant_id', table_name='planning_instructions')
    op.drop_table('planning_instructions')

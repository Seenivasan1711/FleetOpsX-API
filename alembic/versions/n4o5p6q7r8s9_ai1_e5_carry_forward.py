"""ai1_e5_carry_forward

Creates the carry_forward_notes table for AI-1 E5.
Dropped orders get a PENDING note pointing to a suggested driver on Day+1/Day+2.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'n4o5p6q7r8s9'
down_revision = 'm3n4o5p6q7r8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'carry_forward_notes',
        sa.Column('id',                 sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',          sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('order_id',           sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_date',          sa.Date(), nullable=False),
        sa.Column('to_date',            sa.Date(), nullable=False),
        sa.Column('suggested_driver_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('drivers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('context_note',       sa.Text(), nullable=False, server_default=''),
        sa.Column('status',             sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('created_at',         sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at',         sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_cfn_tenant_id',  'carry_forward_notes', ['tenant_id'])
    op.create_index('ix_cfn_order_id',   'carry_forward_notes', ['order_id'])
    op.create_index('ix_cfn_from_date',  'carry_forward_notes', ['from_date'])
    op.create_index('ix_cfn_to_date',    'carry_forward_notes', ['to_date'])
    op.create_index('ix_cfn_status',     'carry_forward_notes', ['status'])


def downgrade() -> None:
    op.drop_index('ix_cfn_status',    table_name='carry_forward_notes')
    op.drop_index('ix_cfn_to_date',   table_name='carry_forward_notes')
    op.drop_index('ix_cfn_from_date', table_name='carry_forward_notes')
    op.drop_index('ix_cfn_order_id',  table_name='carry_forward_notes')
    op.drop_index('ix_cfn_tenant_id', table_name='carry_forward_notes')
    op.drop_table('carry_forward_notes')

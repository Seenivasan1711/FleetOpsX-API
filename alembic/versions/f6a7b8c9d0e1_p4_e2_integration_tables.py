"""p4_e2_integration_tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-06

Adds webhook_registrations and integration_logs tables (P4-E2).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'webhook_registrations',
        sa.Column('id',          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url',         sa.String(500), nullable=False),
        sa.Column('event_types', postgresql.JSON, nullable=False),
        sa.Column('secret',      sa.String(500), nullable=True),
        sa.Column('is_active',   sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_error',  sa.Text(), nullable=True),
        sa.Column('created_at',  sa.DateTime(), nullable=True),
        sa.Column('updated_at',  sa.DateTime(), nullable=True),
    )
    op.create_index('ix_webhook_registrations_tenant_id', 'webhook_registrations', ['tenant_id'])

    op.create_table(
        'integration_logs',
        sa.Column('id',               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('partner_order_id', sa.String(200), nullable=False),
        sa.Column('source_system',    sa.String(100), nullable=False),
        sa.Column('raw_payload',      postgresql.JSON, nullable=True),
        sa.Column('normalized',       sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('order_id',         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message',    sa.Text(), nullable=True),
        sa.Column('created_at',       sa.DateTime(), nullable=True),
        sa.Column('updated_at',       sa.DateTime(), nullable=True),
    )
    op.create_index('ix_integration_logs_tenant_id', 'integration_logs', ['tenant_id'])
    op.create_index('ix_integration_logs_partner_order_id', 'integration_logs', ['partner_order_id'])


def downgrade() -> None:
    op.drop_index('ix_integration_logs_partner_order_id', table_name='integration_logs')
    op.drop_index('ix_integration_logs_tenant_id', table_name='integration_logs')
    op.drop_table('integration_logs')

    op.drop_index('ix_webhook_registrations_tenant_id', table_name='webhook_registrations')
    op.drop_table('webhook_registrations')

"""p4_e3_marketplace_tables

Revision ID: 0a1b2c3d4e5f
Revises: f6a7b8c9d0e1
Create Date: 2026-05-06

Adds capacity_offers, capacity_requests, capacity_matches tables (P4-E3).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0a1b2c3d4e5f'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'capacity_offers',
        sa.Column('id',            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('offer_date',    sa.Date(),    nullable=False),
        sa.Column('driver_count',  sa.Integer(), nullable=False),
        sa.Column('vehicle_type',  sa.String(50), nullable=True),
        sa.Column('zone',          sa.String(100), nullable=False),
        sa.Column('rate_per_stop', sa.Float(),   nullable=True),
        sa.Column('status',        sa.String(20), nullable=False, server_default='OPEN'),
        sa.Column('expires_at',    sa.DateTime(), nullable=False),
        sa.Column('created_at',    sa.DateTime(), nullable=True),
        sa.Column('updated_at',    sa.DateTime(), nullable=True),
    )
    op.create_index('ix_capacity_offers_tenant_id', 'capacity_offers', ['tenant_id'])
    op.create_index('ix_capacity_offers_status',    'capacity_offers', ['status'])
    op.create_index('ix_capacity_offers_zone',      'capacity_offers', ['zone'])

    op.create_table(
        'capacity_requests',
        sa.Column('id',           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_date', sa.Date(),    nullable=False),
        sa.Column('order_count',  sa.Integer(), nullable=False),
        sa.Column('zone',         sa.String(100), nullable=False),
        sa.Column('priority',     sa.String(20), nullable=False, server_default='NORMAL'),
        sa.Column('status',       sa.String(20), nullable=False, server_default='OPEN'),
        sa.Column('expires_at',   sa.DateTime(), nullable=False),
        sa.Column('created_at',   sa.DateTime(), nullable=True),
        sa.Column('updated_at',   sa.DateTime(), nullable=True),
    )
    op.create_index('ix_capacity_requests_tenant_id', 'capacity_requests', ['tenant_id'])
    op.create_index('ix_capacity_requests_status',    'capacity_requests', ['status'])

    op.create_table(
        'capacity_matches',
        sa.Column('id',                    postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('offer_id',              postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('capacity_offers.id',   ondelete='CASCADE'), nullable=False),
        sa.Column('request_id',            postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('capacity_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('offering_tenant_id',    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('requesting_tenant_id',  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('matched_orders',        sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status',                sa.String(20), nullable=False, server_default='PENDING_ACCEPTANCE'),
        sa.Column('settled_at',            sa.DateTime(), nullable=True),
        sa.Column('created_at',            sa.DateTime(), nullable=True),
        sa.Column('updated_at',            sa.DateTime(), nullable=True),
    )
    op.create_index('ix_capacity_matches_offering_tenant',   'capacity_matches', ['offering_tenant_id'])
    op.create_index('ix_capacity_matches_requesting_tenant', 'capacity_matches', ['requesting_tenant_id'])


def downgrade() -> None:
    op.drop_table('capacity_matches')
    op.drop_table('capacity_requests')
    op.drop_table('capacity_offers')

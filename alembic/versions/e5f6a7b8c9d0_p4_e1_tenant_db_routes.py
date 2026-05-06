"""p4_e1_tenant_db_routes

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-06

Adds tenant_db_routes table for per-tenant DB routing (P4-E1).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tenant_db_routes',
        sa.Column('id',                postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('connection_string', sa.String(500), nullable=False),
        sa.Column('region',            sa.String(100), nullable=True),
        sa.Column('is_active',         sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_pool_size',     sa.Integer(), nullable=False, server_default='10'),
        sa.Column('created_at',        sa.DateTime(), nullable=True),
        sa.Column('updated_at',        sa.DateTime(), nullable=True),
    )
    op.create_index('ix_tenant_db_routes_tenant_id', 'tenant_db_routes', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_tenant_db_routes_tenant_id', table_name='tenant_db_routes')
    op.drop_table('tenant_db_routes')

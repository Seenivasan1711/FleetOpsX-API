"""p5_e1_ai_provider_configs

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-05-09

Creates ai_provider_configs table for P5-E1 AI Provider Management.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'h8i9j0k1l2m3'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_provider_configs',
        sa.Column('id',                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',           postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('provider_name',       sa.String(50),  nullable=False),
        sa.Column('model_id',            sa.String(100), nullable=False),
        sa.Column('api_key_enc',         sa.String(500), nullable=True),
        sa.Column('task_type',           sa.String(30),  nullable=False),
        sa.Column('is_active',           sa.Boolean,     nullable=False, server_default='true'),
        sa.Column('is_platform_default', sa.Boolean,     nullable=False, server_default='false'),
        sa.Column('created_at',          sa.DateTime,    server_default=sa.func.now()),
        sa.Column('updated_at',          sa.DateTime,    server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'provider_name', 'task_type', name='uq_ai_provider_tenant_task'),
    )


def downgrade() -> None:
    op.drop_table('ai_provider_configs')

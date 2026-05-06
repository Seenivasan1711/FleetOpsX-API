"""p4_e4_audit_rbac_tables

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-05-06

Adds audit_log_entries and rbac_roles tables (P4-E4).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '1b2c3d4e5f6a'
down_revision = '0a1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_log_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_email', sa.String(200), nullable=False),
        sa.Column('actor_role',  sa.String(50),  nullable=False),
        sa.Column('action',       sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('before_state', postgresql.JSON, nullable=True),
        sa.Column('after_state',  postgresql.JSON, nullable=True),
        sa.Column('ip_address',  sa.String(50),  nullable=True),
        sa.Column('user_agent',  sa.String(200), nullable=True),
        sa.Column('ai_context',  postgresql.JSON, nullable=True),
    )
    op.create_index('ix_audit_log_tenant',        'audit_log_entries', ['tenant_id'])
    op.create_index('ix_audit_log_action',        'audit_log_entries', ['action'])
    op.create_index('ix_audit_log_resource_type', 'audit_log_entries', ['resource_type'])
    op.create_index('ix_audit_log_created_at',    'audit_log_entries', ['created_at'])

    op.create_table(
        'rbac_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name',        sa.String(100), nullable=False),
        sa.Column('permissions', postgresql.ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('is_system',   sa.Boolean, nullable=False, server_default='false'),
    )
    op.create_index('ix_rbac_roles_tenant', 'rbac_roles', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('rbac_roles')
    op.drop_index('ix_audit_log_created_at',    'audit_log_entries')
    op.drop_index('ix_audit_log_resource_type', 'audit_log_entries')
    op.drop_index('ix_audit_log_action',        'audit_log_entries')
    op.drop_index('ix_audit_log_tenant',        'audit_log_entries')
    op.drop_table('audit_log_entries')

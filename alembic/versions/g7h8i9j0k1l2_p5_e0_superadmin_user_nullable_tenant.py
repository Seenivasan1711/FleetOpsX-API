"""p5_e0_superadmin_user_nullable_tenant

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-09

Allow users.tenant_id to be NULL so the superadmin user can exist without a tenant.
"""
from alembic import op
import sqlalchemy as sa


revision = 'g7h8i9j0k1l2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('users', 'tenant_id', nullable=True)


def downgrade() -> None:
    # Only safe if no superadmin user exists
    op.execute("DELETE FROM users WHERE role = 'superadmin' AND tenant_id IS NULL")
    op.alter_column('users', 'tenant_id', nullable=False)

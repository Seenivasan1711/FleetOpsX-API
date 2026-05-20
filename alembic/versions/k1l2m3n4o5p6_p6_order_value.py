"""p6 order value field

Revision ID: k1l2m3n4o5p6
Revises: 1e152af392fb
Create Date: 2026-05-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l2m3n4o5p6'
down_revision = '1e152af392fb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('value', sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'value')

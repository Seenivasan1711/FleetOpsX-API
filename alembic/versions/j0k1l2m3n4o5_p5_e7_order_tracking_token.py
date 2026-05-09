"""p5_e7_order_tracking_token

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'j0k1l2m3n4o5'
down_revision = 'i9j0k1l2m3n4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('tracking_token', postgresql.UUID(as_uuid=True), nullable=True, unique=False),
    )
    op.create_index('ix_orders_tracking_token', 'orders', ['tracking_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_orders_tracking_token', table_name='orders')
    op.drop_column('orders', 'tracking_token')

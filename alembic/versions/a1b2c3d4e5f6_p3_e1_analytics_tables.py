"""p3_e1_analytics_tables

Revision ID: a1b2c3d4e5f6
Revises: 3abca364f966
Create Date: 2026-03-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3abca364f966'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'delivery_analytics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('driver_id', sa.UUID(), nullable=True),
        sa.Column('route_plan_id', sa.UUID(), nullable=True),
        sa.Column('delivery_date', sa.Date(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('hour_of_day', sa.Integer(), nullable=True),
        sa.Column('zone', sa.String(100), nullable=True),
        sa.Column('planned_eta', sa.String(8), nullable=True),
        sa.Column('actual_arrival', sa.DateTime(), nullable=True),
        sa.Column('delay_minutes', sa.Integer(), nullable=True),
        sa.Column('was_on_time', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=False, server_default='NORMAL'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['route_plan_id'], ['route_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
    )
    op.create_index(op.f('ix_delivery_analytics_delivery_date'), 'delivery_analytics', ['delivery_date'], unique=False)
    op.create_index(op.f('ix_delivery_analytics_driver_id'), 'delivery_analytics', ['driver_id'], unique=False)
    op.create_index(op.f('ix_delivery_analytics_order_id'), 'delivery_analytics', ['order_id'], unique=False)
    op.create_index(op.f('ix_delivery_analytics_route_plan_id'), 'delivery_analytics', ['route_plan_id'], unique=False)
    op.create_index(op.f('ix_delivery_analytics_tenant_id'), 'delivery_analytics', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_delivery_analytics_zone'), 'delivery_analytics', ['zone'], unique=False)

    op.create_table(
        'driver_performance_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('driver_id', sa.UUID(), nullable=False),
        sa.Column('score_date', sa.Date(), nullable=False),
        sa.Column('total_deliveries', sa.Integer(), nullable=True),
        sa.Column('on_time_count', sa.Integer(), nullable=True),
        sa.Column('on_time_rate', sa.Float(), nullable=True),
        sa.Column('avg_delay_min', sa.Float(), nullable=True),
        sa.Column('total_delay_min', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_driver_performance_scores_driver_id'), 'driver_performance_scores', ['driver_id'], unique=False)
    op.create_index(op.f('ix_driver_performance_scores_score_date'), 'driver_performance_scores', ['score_date'], unique=False)
    op.create_index(op.f('ix_driver_performance_scores_tenant_id'), 'driver_performance_scores', ['tenant_id'], unique=False)
    # Composite unique: one row per driver per date per tenant
    op.create_index('ix_dps_driver_date', 'driver_performance_scores', ['driver_id', 'score_date'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_dps_driver_date', table_name='driver_performance_scores')
    op.drop_index(op.f('ix_driver_performance_scores_tenant_id'), table_name='driver_performance_scores')
    op.drop_index(op.f('ix_driver_performance_scores_score_date'), table_name='driver_performance_scores')
    op.drop_index(op.f('ix_driver_performance_scores_driver_id'), table_name='driver_performance_scores')
    op.drop_table('driver_performance_scores')

    op.drop_index(op.f('ix_delivery_analytics_zone'), table_name='delivery_analytics')
    op.drop_index(op.f('ix_delivery_analytics_tenant_id'), table_name='delivery_analytics')
    op.drop_index(op.f('ix_delivery_analytics_route_plan_id'), table_name='delivery_analytics')
    op.drop_index(op.f('ix_delivery_analytics_order_id'), table_name='delivery_analytics')
    op.drop_index(op.f('ix_delivery_analytics_driver_id'), table_name='delivery_analytics')
    op.drop_index(op.f('ix_delivery_analytics_delivery_date'), table_name='delivery_analytics')
    op.drop_table('delivery_analytics')

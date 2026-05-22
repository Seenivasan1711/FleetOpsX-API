"""ai1_e2_savings_columns

Adds baseline_km, baseline_hrs, km_saved, hrs_saved to route_plans so the
AI-1 runner can persist the "AI saved X km vs naive routing" metric.

Also adds total_distance_km, km_saved, hrs_saved to plan_history so the
Plan History page can show savings per confirmed plan.

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l2m3n4o5p6'
down_revision = 'j0k1l2m3n4o5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # route_plans — savings vs naive baseline
    op.add_column('route_plans', sa.Column('baseline_km',  sa.Float(), nullable=True))
    op.add_column('route_plans', sa.Column('baseline_hrs', sa.Float(), nullable=True))
    op.add_column('route_plans', sa.Column('km_saved',     sa.Float(), nullable=True))
    op.add_column('route_plans', sa.Column('hrs_saved',    sa.Float(), nullable=True))

    # plan_history — savings for Plan History page
    op.add_column('plan_history', sa.Column('total_distance_km', sa.Float(), nullable=True))
    op.add_column('plan_history', sa.Column('km_saved',          sa.Float(), nullable=True))
    op.add_column('plan_history', sa.Column('hrs_saved',         sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('plan_history', 'hrs_saved')
    op.drop_column('plan_history', 'km_saved')
    op.drop_column('plan_history', 'total_distance_km')
    op.drop_column('route_plans', 'hrs_saved')
    op.drop_column('route_plans', 'km_saved')
    op.drop_column('route_plans', 'baseline_hrs')
    op.drop_column('route_plans', 'baseline_km')

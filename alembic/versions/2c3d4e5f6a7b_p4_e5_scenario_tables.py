"""p4_e5_scenario_tables

Revision ID: 2c3d4e5f6a7b
Revises: 1b2c3d4e5f6a
Create Date: 2026-05-06

Adds scenario_runs and scenario_results tables (P4-E5).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2c3d4e5f6a7b'
down_revision = '1b2c3d4e5f6a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scenario_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name',          sa.String(200), nullable=False),
        sa.Column('scenario_type', sa.String(50),  nullable=False),
        sa.Column('parameters',    postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('horizon_start', sa.Date, nullable=False),
        sa.Column('horizon_days',  sa.Integer, nullable=False, server_default='7'),
        sa.Column('status',        sa.String(20), nullable=False, server_default='QUEUED'),
        sa.Column('baseline_kpis', postgresql.JSON, nullable=True),
        sa.Column('created_by',    sa.String(100), nullable=False),
        sa.Column('completed_at',  sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_scenario_runs_tenant', 'scenario_runs', ['tenant_id'])
    op.create_index('ix_scenario_runs_status', 'scenario_runs', ['status'])

    op.create_table(
        'scenario_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scenario_run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('scenario_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_date',          sa.Date,    nullable=False),
        sa.Column('total_routes',       sa.Integer, nullable=False, server_default='0'),
        sa.Column('assigned_orders',    sa.Integer, nullable=False, server_default='0'),
        sa.Column('on_time_rate',       sa.Float,   nullable=False, server_default='0'),
        sa.Column('avg_delay_min',      sa.Float,   nullable=False, server_default='0'),
        sa.Column('total_distance_km',  sa.Float,   nullable=False, server_default='0'),
        sa.Column('fleet_utilization',  sa.Float,   nullable=False, server_default='0'),
        sa.Column('kpi_delta',          postgresql.JSON, nullable=True),
    )
    op.create_index('ix_scenario_results_run', 'scenario_results', ['scenario_run_id'])


def downgrade() -> None:
    op.drop_index('ix_scenario_results_run', 'scenario_results')
    op.drop_table('scenario_results')
    op.drop_index('ix_scenario_runs_status', 'scenario_runs')
    op.drop_index('ix_scenario_runs_tenant', 'scenario_runs')
    op.drop_table('scenario_runs')

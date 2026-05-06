"""pp_e3_driver_availability_vehicle_status

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'driver_availability',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('driver_id', sa.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('shift_start', sa.Time(), nullable=True),
        sa.Column('shift_end', sa.Time(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='available'),
        sa.Column('hours_worked_today', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('driver_id', 'date', name='uq_driver_availability_driver_date'),
    )
    op.create_index('ix_driver_availability_driver_id', 'driver_availability', ['driver_id'])
    op.create_index('ix_driver_availability_date', 'driver_availability', ['date'])
    op.create_index('ix_driver_availability_tenant_id', 'driver_availability', ['tenant_id'])

    op.create_table(
        'vehicle_status',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('vehicle_id', sa.UUID(), nullable=False),
        sa.Column('current_mileage', sa.Float(), nullable=True),
        sa.Column('fuel_level_pct', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='available'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vehicle_id', name='uq_vehicle_status_vehicle'),
    )
    op.create_index('ix_vehicle_status_vehicle_id', 'vehicle_status', ['vehicle_id'])
    op.create_index('ix_vehicle_status_tenant_id', 'vehicle_status', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_vehicle_status_tenant_id', table_name='vehicle_status')
    op.drop_index('ix_vehicle_status_vehicle_id', table_name='vehicle_status')
    op.drop_table('vehicle_status')

    op.drop_index('ix_driver_availability_tenant_id', table_name='driver_availability')
    op.drop_index('ix_driver_availability_date', table_name='driver_availability')
    op.drop_index('ix_driver_availability_driver_id', table_name='driver_availability')
    op.drop_table('driver_availability')

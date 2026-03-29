"""p3_e2_agent_suggestions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-29 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'agent_suggestions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('plan_date', sa.Date(), nullable=False),
        sa.Column('suggestion_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='NORMAL'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('acted_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_suggestions_plan_date'), 'agent_suggestions', ['plan_date'], unique=False)
    op.create_index(op.f('ix_agent_suggestions_status'), 'agent_suggestions', ['status'], unique=False)
    op.create_index(op.f('ix_agent_suggestions_tenant_id'), 'agent_suggestions', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_suggestions_tenant_id'), table_name='agent_suggestions')
    op.drop_index(op.f('ix_agent_suggestions_status'), table_name='agent_suggestions')
    op.drop_index(op.f('ix_agent_suggestions_plan_date'), table_name='agent_suggestions')
    op.drop_table('agent_suggestions')

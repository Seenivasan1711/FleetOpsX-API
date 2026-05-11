"""merge_all_heads

Revision ID: 1e152af392fb
Revises: 2c3d4e5f6a7b, j0k1l2m3n4o5
Create Date: 2026-05-09 12:07:15.646516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e152af392fb'
down_revision: Union[str, Sequence[str], None] = ('2c3d4e5f6a7b', 'j0k1l2m3n4o5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

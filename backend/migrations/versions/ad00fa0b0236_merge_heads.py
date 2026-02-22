"""merge_heads

Revision ID: ad00fa0b0236
Revises: 45becff42dc6, c4ca9e2d58e6
Create Date: 2026-02-22 20:42:32.096615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad00fa0b0236'
down_revision: Union[str, Sequence[str], None] = ('45becff42dc6', 'c4ca9e2d58e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

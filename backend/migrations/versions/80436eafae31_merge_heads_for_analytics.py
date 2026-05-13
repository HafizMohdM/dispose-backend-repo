"""merge_heads_for_analytics

Revision ID: 80436eafae31
Revises: 0e0636f191fe, 64fb8fe38c5f
Create Date: 2026-05-09 21:47:23.660254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80436eafae31'
down_revision: Union[str, Sequence[str], None] = ('0e0636f191fe', '64fb8fe38c5f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

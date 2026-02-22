"""merge heads

Revision ID: b7680702cb6a
Revises: 7b66df4529fc, d4e5f6g7h8i9
Create Date: 2026-02-22 14:44:49.652666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7680702cb6a'
down_revision: Union[str, Sequence[str], None] = ('7b66df4529fc', 'd4e5f6g7h8i9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

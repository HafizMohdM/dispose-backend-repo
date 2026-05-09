"""seed_analytics_permissions

Revision ID: 64fb8fe38c5f
Revises: 4f907290aa32
Create Date: 2026-05-09 18:59:54.707878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64fb8fe38c5f'
down_revision: Union[str, Sequence[str], None] = '4f907290aa32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

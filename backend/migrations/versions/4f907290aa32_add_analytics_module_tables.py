"""add_analytics_module_tables

Revision ID: 4f907290aa32
Revises: d8e3ea99e480
Create Date: 2026-05-09 18:59:02.242193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4f907290aa32'
down_revision: Union[str, Sequence[str], None] = 'd8e3ea99e480'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    pass
    # ### end Alembic commands ###

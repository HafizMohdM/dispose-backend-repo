"""seed rbac roles and permissions

Revision ID: b8a9479380e9
Revises: 06994352ffda
Create Date: 2026-02-12 17:08:30.020950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8a9479380e9'
down_revision: Union[str, Sequence[str], None] = '06994352ffda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

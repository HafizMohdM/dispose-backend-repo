"""merge_audit_logs_head

Revision ID: 2385556f95e3
Revises: ad00fa0b0236, dcbbfe269d3f
Create Date: 2026-02-22 22:50:38.323845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2385556f95e3'
down_revision: Union[str, Sequence[str], None] = ('ad00fa0b0236', 'dcbbfe269d3f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

"""add session metadata columns

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_sessions', sa.Column('ip_address', sa.String(45), nullable=True))
    op.add_column('user_sessions', sa.Column('device_name', sa.String(255), nullable=True))
    op.add_column('user_sessions', sa.Column('user_agent', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_sessions', 'user_agent')
    op.drop_column('user_sessions', 'device_name')
    op.drop_column('user_sessions', 'ip_address')

"""add failed_attempts to user_sessions and create audit_logs table

Revision ID: a1b2c3d4e5f6
Revises: 60c26fdc1532
Create Date: 2026-02-20 17:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '60c26fdc1532'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add failed_attempts column to user_sessions
    op.add_column('user_sessions', sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'))

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('meta', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_column('user_sessions', 'failed_attempts')

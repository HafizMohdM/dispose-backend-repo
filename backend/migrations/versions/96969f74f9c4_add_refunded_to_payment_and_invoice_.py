"""add_refunded_to_payment_and_invoice_enums

Revision ID: 96969f74f9c4
Revises: a16819c4e821
Create Date: 2026-02-24 15:12:29.971414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96969f74f9c4'
down_revision: Union[str, Sequence[str], None] = 'a16819c4e821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use autocommit block for ALTER TYPE which cannot run inside a transaction block in older postgres
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'REFUNDED'")
        op.execute("ALTER TYPE invoicestatus ADD VALUE IF NOT EXISTS 'REFUNDED'")


def downgrade() -> None:
    """Downgrade schema."""
    pass

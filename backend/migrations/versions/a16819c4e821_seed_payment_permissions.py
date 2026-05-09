"""seed_payment_permissions

Revision ID: a16819c4e821
Revises: 7f1ddeb4c3f9
Create Date: 2026-02-24 13:17:15.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a16819c4e821'
down_revision: Union[str, Sequence[str], None] = '7f1ddeb4c3f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PAYMENT_PERMISSIONS = [
    {"code": "payment.manage", "description": "Full access to manage and view all payments and invoices"},
    {"code": "payment.view", "description": "View associated invoices and payment attempts"},
]

ADMIN_PERMISSIONS = [
    "payment.manage", "payment.view"
]

def upgrade() -> None:
    conn = op.get_bind()

    # Insert new permissions
    for perm in PAYMENT_PERMISSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (code, description, created_at, updated_at) "
                "VALUES (:code, :desc, NOW(), NOW()) "
                "ON CONFLICT DO NOTHING"
            ),
            {"code": perm["code"], "desc": perm["description"]},
        )

    # Get ADMIN role id
    result = conn.execute(sa.text("SELECT id FROM roles WHERE name = 'ADMIN'")).fetchone()
    if not result:
        return
    admin_role_id = result[0]

    # Map permissions to ADMIN role
    for perm_code in ADMIN_PERMISSIONS:
        perm_result = conn.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": perm_code},
        ).fetchone()
        if perm_result:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) "
                    "VALUES (:role_id, :perm_id, NOW(), NOW()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"role_id": admin_role_id, "perm_id": perm_result[0]},
            )

def downgrade() -> None:
    conn = op.get_bind()
    codes = [p["code"] for p in PAYMENT_PERMISSIONS]
    for code in codes:
        conn.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE permission_id = "
                "(SELECT id FROM permissions WHERE code = :code)"
            ),
            {"code": code},
        )
        conn.execute(
            sa.text("DELETE FROM permissions WHERE code = :code"),
            {"code": code},
        )

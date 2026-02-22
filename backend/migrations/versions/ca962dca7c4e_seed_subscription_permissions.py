"""seed_subscription_permissions

Revision ID: ca962dca7c4e
Revises: 0950167b74fa
Create Date: 2026-02-22 16:16:04.042283

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca962dca7c4e'
down_revision: Union[str, Sequence[str], None] = '0950167b74fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SUBSCRIPTION_PERMISSIONS = [
    {"code": "subscription.manage", "description": "Create, update, and delete subscription plans"},
    {"code": "subscription.view", "description": "View subscription plans and subscribe to them"},
]

ADMIN_PERMISSIONS = [
    "subscription.manage", "subscription.view"
]

def upgrade() -> None:
    conn = op.get_bind()

    # Insert new permissions
    for perm in SUBSCRIPTION_PERMISSIONS:
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
    codes = [p["code"] for p in SUBSCRIPTION_PERMISSIONS]
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

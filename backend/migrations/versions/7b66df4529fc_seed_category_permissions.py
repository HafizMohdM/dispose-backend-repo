"""seed_category_permissions

Revision ID: 7b66df4529fc
Revises: 60c26fdc1532
Create Date: 2026-02-20 17:17:10.452507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b66df4529fc'
down_revision: Union[str, Sequence[str], None] = '60c26fdc1532'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_PERMISSIONS = [
    {"code": "category.create", "description": "Create organization category"},
    {"code": "category.view", "description": "View organization categories"},
    {"code": "category.update", "description": "Update organization category"},
    {"code": "category.delete", "description": "Delete organization category"},
    {"code": "organization.create", "description": "Create organization"},
    {"code": "organization.view", "description": "View organizations"},
    {"code": "organization.update", "description": "Update organization"},
    {"code": "organization.approve", "description": "Approve organization"},
]

ADMIN_PERMISSIONS = [
    "category.create", "category.view", "category.update", "category.delete",
    "organization.create", "organization.view", "organization.update", "organization.approve",
]


def upgrade() -> None:
    conn = op.get_bind()

    # Insert new permissions
    for perm in CATEGORY_PERMISSIONS:
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
    codes = [p["code"] for p in CATEGORY_PERMISSIONS]
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

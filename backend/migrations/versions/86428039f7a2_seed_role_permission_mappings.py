"""seed role permission mappings

Revision ID: 86428039f7a2
Revises: b8a9479380e9
Create Date: 2026-02-12 17:50:09.862617

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "86428039f7a2"
down_revision = "b8a9479380e9"
branch_labels = None
depends_on = None


ROLE_PERMISSION_MAP = {
    "ADMIN": [
        "auth.login",
        "pickup.create",
        "pickup.view",
        "pickup.assign",
        "pickup.complete",
        "org.manage",
        "report.view",
    ],
    "COMPANY": [
        "pickup.create",
        "pickup.view",
        "pickup.assign",
        "org.manage",
        "report.view",
    ],
    "DRIVER": [
        "pickup.view",
        "pickup.complete",
    ],
    "CUSTOMER": [
        "pickup.create",
        "pickup.view",
    ],
}


def upgrade():
    conn = op.get_bind()

    role_ids = dict(
        conn.execute(sa.text("SELECT name, id FROM roles")).fetchall()
    )
    permission_ids = dict(
        conn.execute(sa.text("SELECT code, id FROM permissions")).fetchall()
    )

    for role, perms in ROLE_PERMISSION_MAP.items():
        role_id = role_ids.get(role)
        for perm in perms:
            perm_id = permission_ids.get(perm)
            if role_id and perm_id:
                conn.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) "
                        "VALUES (:role_id, :perm_id, NOW(), NOW()) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"role_id": role_id, "perm_id": perm_id},
                )


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_permissions"))


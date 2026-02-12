"""roles and permissions

Revision ID: 06994352ffda
Revises: cbef3d25a919
Create Date: 2026-02-12 16:52:06.289006

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "06994352ffda"
down_revision = "cbef3d25a919"
branch_labels = None
depends_on = None


ROLES = [
    {"name": "ADMIN", "description": "Platform administrator"},
    {"name": "COMPANY", "description": "Organization operator"},
    {"name": "DRIVER", "description": "Pickup driver"},
    {"name": "CUSTOMER", "description": "Organization customer"},
]

PERMISSIONS = [
    {"code": "auth.login", "description": "Login to system"},
    {"code": "pickup.create", "description": "Create pickup request"},
    {"code": "pickup.view", "description": "View pickup details"},
    {"code": "pickup.assign", "description": "Assign pickup to driver"},
    {"code": "pickup.complete", "description": "Complete pickup"},
    {"code": "org.manage", "description": "Manage organization"},
    {"code": "report.view", "description": "View reports"},
]


def upgrade():
    conn = op.get_bind()

    for role in ROLES:
        conn.execute(
            sa.text(
                "INSERT INTO roles (name, description, created_at, updated_at) "
                "VALUES (:name, :description, NOW(), NOW()) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            role,
        )

    for perm in PERMISSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (code, description, created_at, updated_at) "
                "VALUES (:code, :description, NOW(), NOW()) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            perm,
        )


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_permissions"))
    conn.execute(sa.text("DELETE FROM permissions"))
    conn.execute(sa.text("DELETE FROM roles"))

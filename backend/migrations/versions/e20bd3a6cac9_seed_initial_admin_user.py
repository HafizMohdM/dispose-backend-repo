"""seed initial admin user

Revision ID: e20bd3a6cac9
Revises: 86428039f7a2
Create Date: 2026-02-12 18:23:11.217447

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e20bd3a6cac9"
down_revision = "86428039f7a2"
branch_labels = None
depends_on = None


ADMIN_MOBILE = "9999999999"


def upgrade():
    conn = op.get_bind()

    # insert default organization
    org_result = conn.execute(
        sa.text(
            "INSERT INTO organizations (name, description, created_at, updated_at) "
            "VALUES ('System', 'Default System Organization', NOW(), NOW()) "
            "ON CONFLICT (name) DO NOTHING "
            "RETURNING id"
        )
    ).fetchone()

    if org_result:
        org_id = org_result[0]
    else:
        org_id = conn.execute(
            sa.text("SELECT id FROM organizations WHERE name = 'System'")
        ).fetchone()[0]

    # insert admin user
    result = conn.execute(
        sa.text(
            "INSERT INTO users (mobile, is_active, created_at, updated_at) "
            "VALUES (:mobile, true, NOW(), NOW()) "
            "ON CONFLICT (mobile) DO NOTHING "
            "RETURNING id"
        ),
        {"mobile": ADMIN_MOBILE},
    ).fetchone()

    if result:
        user_id = result[0]
    else:
        user_id = conn.execute(
            sa.text("SELECT id FROM users WHERE mobile = :mobile"),
            {"mobile": ADMIN_MOBILE},
        ).fetchone()[0]

    # get ADMIN role
    role_id = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'ADMIN'")
    ).fetchone()[0]

    # assign role
    conn.execute(
        sa.text(
            "INSERT INTO user_roles (user_id, role_id, org_id, created_at, updated_at) "
            "VALUES (:user_id, :role_id, :org_id, NOW(), NOW()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"user_id": user_id, "role_id": role_id, "org_id": org_id},
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM user_roles WHERE user_id IN "
            "(SELECT id FROM users WHERE mobile = :mobile)"
        ),
        {"mobile": ADMIN_MOBILE},
    )
    conn.execute(
        sa.text("DELETE FROM users WHERE mobile = :mobile"),
        {"mobile": ADMIN_MOBILE},
    )


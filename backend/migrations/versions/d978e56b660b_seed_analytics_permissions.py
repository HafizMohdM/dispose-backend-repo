"""seed_analytics_permissions

Revision ID: d978e56b660b
Revises: a0a6e8529400
Create Date: 2026-05-09 22:05:24.285127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd978e56b660b'
down_revision: Union[str, Sequence[str], None] = 'a0a6e8529400'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection
    bind = op.get_bind()
    
    # Define permissions to add
    permissions = [
        {"code": "analytics.view", "description": "Access to analytics dashboards"},
        {"code": "analytics.export", "description": "Ability to export analytics data"},
        {"code": "analytics.admin", "description": "Access to security and audit analytics"},
    ]
    
    # Insert permissions
    for perm in permissions:
        bind.execute(
            sa.text("INSERT INTO permissions (code, description, created_at, updated_at) VALUES (:code, :description, now(), now()) ON CONFLICT (code) DO NOTHING"),
            perm
        )

    
    # Map permissions to roles (ADMIN and SUPER_ADMIN)
    roles_to_map = ["ADMIN", "SUPER_ADMIN"]
    for role_name in roles_to_map:
        role = bind.execute(sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).fetchone()
        if role:
            role_id = role[0]
            for perm in permissions:
                perm_id_res = bind.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": perm["code"]}).fetchone()
                if perm_id_res:
                    perm_id = perm_id_res[0]
                    bind.execute(
                        sa.text("INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (:role_id, :permission_id, now(), now()) ON CONFLICT DO NOTHING"),
                        {"role_id": role_id, "permission_id": perm_id}
                    )



def downgrade() -> None:
    bind = op.get_bind()
    codes = ("analytics.view", "analytics.export", "analytics.admin")
    bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN :codes)"), {"codes": codes})
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": codes})

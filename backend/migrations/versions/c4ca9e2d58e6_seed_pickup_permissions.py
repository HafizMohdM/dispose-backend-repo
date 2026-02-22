"""seed_pickup_permissions

Revision ID: c4ca9e2d58e6
Revises: 2280c99d3606
Create Date: 2026-02-22 17:52:16.862724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4ca9e2d58e6'
down_revision: Union[str, Sequence[str], None] = '2280c99d3606'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Insert permissions
    op.execute("""
        INSERT INTO permissions (code, description, created_at, updated_at)
        VALUES 
            ('pickup.create', 'Can create pickups', NOW(), NOW()),
            ('pickup.manage', 'Can assign drivers and cancel any pickup', NOW(), NOW()),
            ('pickup.view', 'Can view pickups', NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # 2. Get Role IDs
    op.execute("""
        DO $$
        DECLARE
            admin_role_id INT;
            org_role_id INT;
            driver_role_id INT;
            perm_create_id INT;
            perm_manage_id INT;
            perm_view_id INT;
        BEGIN
            -- Ensure generic roles exist just in case
            INSERT INTO roles (name, description, created_at, updated_at) VALUES ('ADMIN', 'System Admin', NOW(), NOW()) ON CONFLICT (name) DO NOTHING;
            INSERT INTO roles (name, description, created_at, updated_at) VALUES ('ORGANIZATION', 'Org Admin', NOW(), NOW()) ON CONFLICT (name) DO NOTHING;
            INSERT INTO roles (name, description, created_at, updated_at) VALUES ('DRIVER', 'Driver', NOW(), NOW()) ON CONFLICT (name) DO NOTHING;

            SELECT id INTO admin_role_id FROM roles WHERE name = 'ADMIN';
            SELECT id INTO org_role_id FROM roles WHERE name = 'ORGANIZATION';
            SELECT id INTO driver_role_id FROM roles WHERE name = 'DRIVER';

            SELECT id INTO perm_create_id FROM permissions WHERE code = 'pickup.create';
            SELECT id INTO perm_manage_id FROM permissions WHERE code = 'pickup.manage';
            SELECT id INTO perm_view_id FROM permissions WHERE code = 'pickup.view';

            -- ADMIN gets all
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_create_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_manage_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_view_id, NOW(), NOW()) ON CONFLICT DO NOTHING;

            -- ORGANIZATION gets view and create
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (org_role_id, perm_create_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (org_role_id, perm_view_id, NOW(), NOW()) ON CONFLICT DO NOTHING;

            -- DRIVER gets view
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (driver_role_id, perm_view_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE code IN ('pickup.create', 'pickup.manage', 'pickup.view')
        );
        DELETE FROM permissions WHERE code IN ('pickup.create', 'pickup.manage', 'pickup.view');
    """)

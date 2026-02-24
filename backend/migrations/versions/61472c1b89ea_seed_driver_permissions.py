"""seed_driver_permissions

Revision ID: 61472c1b89ea
Revises: 8279a5a0fb15
Create Date: 2026-02-23 14:58:45.603719

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61472c1b89ea'
down_revision: Union[str, Sequence[str], None] = '8279a5a0fb15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Insert Driver Permissions
    op.execute(
        """
        INSERT INTO permissions (code, description, created_at, updated_at) VALUES 
        ('driver:view', 'View driver details', NOW(), NOW()),
        ('driver:create', 'Create new drivers', NOW(), NOW()),
        ('driver:update', 'Update driver details and assign/unassign', NOW(), NOW()),
        ('driver:delete', 'Delete drivers', NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
        """
    )
    
    # 2. Map Permissions to Roles
    # ADMIN gets all 4
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at)
        SELECT r.id, p.id, NOW(), NOW()
        FROM roles r, permissions p
        WHERE r.name = 'ADMIN' 
        AND p.code IN ('driver:view', 'driver:create', 'driver:update', 'driver:delete')
        ON CONFLICT DO NOTHING;
        """
    )
    
    # ORGANIZATION gets all 4
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at)
        SELECT r.id, p.id, NOW(), NOW()
        FROM roles r, permissions p
        WHERE r.name = 'ORGANIZATION' 
        AND p.code IN ('driver:view', 'driver:create', 'driver:update', 'driver:delete')
        ON CONFLICT DO NOTHING;
        """
    )

    # DRIVER gets view only (to fetch their own info)
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at)
        SELECT r.id, p.id, NOW(), NOW()
        FROM roles r, permissions p
        WHERE r.name = 'DRIVER' 
        AND p.code IN ('driver:view')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Remove mapping
    op.execute(
        """
        DELETE FROM role_permissions 
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE code IN ('driver:view', 'driver:create', 'driver:update', 'driver:delete')
        );
        """
    )
    
    # 2. Remove permissions
    op.execute(
        """
        DELETE FROM permissions 
        WHERE code IN ('driver:view', 'driver:create', 'driver:update', 'driver:delete');
        """
    )

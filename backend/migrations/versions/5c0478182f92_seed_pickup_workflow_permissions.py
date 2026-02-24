"""seed_pickup_workflow_permissions

Revision ID: 5c0478182f92
Revises: 2385556f95e3
Create Date: 2026-02-23 12:38:48.804659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c0478182f92'
down_revision: Union[str, Sequence[str], None] = '2385556f95e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Insert permissions
    op.execute("""
        INSERT INTO permissions (code, description, created_at, updated_at)
        VALUES 
            ('pickup.cancel', 'Can cancel a pickup', NOW(), NOW()),
            ('pickup.reschedule', 'Can reschedule a pickup', NOW(), NOW()),
            ('pickup.accept', 'Can accept a pickup assignment', NOW(), NOW()),
            ('pickup.reject', 'Can reject a pickup assignment', NOW(), NOW()),
            ('pickup.complete', 'Can complete a pickup', NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # 2. Get Role IDs and Map
    op.execute("""
        DO $$
        DECLARE
            admin_role_id INT;
            org_role_id INT;
            driver_role_id INT;
            
            perm_cancel_id INT;
            perm_reschedule_id INT;
            perm_accept_id INT;
            perm_reject_id INT;
            perm_complete_id INT;
        BEGIN
            SELECT id INTO admin_role_id FROM roles WHERE name = 'ADMIN';
            SELECT id INTO org_role_id FROM roles WHERE name = 'ORGANIZATION';
            SELECT id INTO driver_role_id FROM roles WHERE name = 'DRIVER';

            SELECT id INTO perm_cancel_id FROM permissions WHERE code = 'pickup.cancel';
            SELECT id INTO perm_reschedule_id FROM permissions WHERE code = 'pickup.reschedule';
            SELECT id INTO perm_accept_id FROM permissions WHERE code = 'pickup.accept';
            SELECT id INTO perm_reject_id FROM permissions WHERE code = 'pickup.reject';
            SELECT id INTO perm_complete_id FROM permissions WHERE code = 'pickup.complete';

            -- ADMIN gets all
            IF admin_role_id IS NOT NULL THEN
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_cancel_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_reschedule_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_accept_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_reject_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (admin_role_id, perm_complete_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
            END IF;

            -- ORGANIZATION gets cancel, reschedule
            IF org_role_id IS NOT NULL THEN
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (org_role_id, perm_cancel_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (org_role_id, perm_reschedule_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
            END IF;

            -- DRIVER gets accept, reject, complete
            IF driver_role_id IS NOT NULL THEN
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (driver_role_id, perm_accept_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (driver_role_id, perm_reject_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
                INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at) VALUES (driver_role_id, perm_complete_id, NOW(), NOW()) ON CONFLICT DO NOTHING;
            END IF;
        END $$;
    """)

def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE code IN ('pickup.cancel', 'pickup.reschedule', 'pickup.accept', 'pickup.reject', 'pickup.complete')
        );
        DELETE FROM permissions WHERE code IN ('pickup.cancel', 'pickup.reschedule', 'pickup.accept', 'pickup.reject', 'pickup.complete');
    """)

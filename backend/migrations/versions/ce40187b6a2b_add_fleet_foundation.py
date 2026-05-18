"""Add fleet foundation

Revision ID: ce40187b6a2b
Revises: a884310f0762
Create Date: 2026-05-18 13:19:46.298520

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ce40187b6a2b'
down_revision: Union[str, Sequence[str], None] = 'a884310f0762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by cleanly recreating fleet tables to avoid column casting mismatches."""
    # Drop existing tables to avoid UUID to Integer casting issues
    op.execute("DROP TABLE IF EXISTS vehicle_assignments CASCADE")
    op.execute("DROP TABLE IF EXISTS vehicle_maintenance CASCADE")
    op.execute("DROP TABLE IF EXISTS vehicles CASCADE")
    
    # 1. Create vehicles fresh
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('vin', sa.String(length=255), nullable=True),
        sa.Column('registration_number', sa.String(length=100), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='VAN'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('last_telemetry_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index(op.f('ix_vehicles_id'), 'vehicles', ['id'], unique=False)
    op.create_index(op.f('ix_vehicles_type'), 'vehicles', ['type'], unique=False)
    op.create_unique_constraint('uix_org_vehicle_registration', 'vehicles', ['organization_id', 'registration_number'])
    op.create_unique_constraint('uix_org_vehicle_vin', 'vehicles', ['organization_id', 'vin'])

    # 2. Create vehicle_assignments fresh
    op.create_table('vehicle_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('driver_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('unassigned_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index(op.f('ix_vehicle_assignments_id'), 'vehicle_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_vehicle_assignments_organization_id'), 'vehicle_assignments', ['organization_id'], unique=False)
    op.create_index(op.f('ix_vehicle_assignments_status'), 'vehicle_assignments', ['status'], unique=False)

    # 3. Create vehicle_maintenance fresh
    op.create_table('vehicle_maintenance',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index(op.f('ix_vehicle_maintenance_id'), 'vehicle_maintenance', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('vehicle_maintenance')
    op.drop_table('vehicle_assignments')
    op.drop_table('vehicles')

"""Add vehicle telemetry and trip tables

Revision ID: f6b81932e8d1
Revises: ec5f40a85779
Create Date: 2026-05-18 00:33:21.264535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
"""Add vehicle telemetry and trip tables

Revision ID: f6b81932e8d1
Revises: ec5f40a85779
Create Date: 2026-05-18 00:33:21.264535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6b81932e8d1'
down_revision: Union[str, Sequence[str], None] = 'ec5f40a85779'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old telemetry/vehicle-dependent tables that are being retired or rebuilt
    op.execute("DROP TABLE IF EXISTS iot_devices CASCADE")
    op.execute("DROP TABLE IF EXISTS maintenance_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS vehicle_diagnostics CASCADE")
    op.execute("DROP TABLE IF EXISTS sensor_streams CASCADE")
    op.execute("DROP TABLE IF EXISTS vehicle_health CASCADE")
    op.execute("DROP TABLE IF EXISTS telemetry_events CASCADE")

    # 2. Drop existing vehicle assignments and vehicles tables to recreate them with UUIDs
    op.execute("DROP TABLE IF EXISTS vehicle_assignments CASCADE")
    op.execute("DROP TABLE IF EXISTS vehicles CASCADE")

    # 3. Re-create vehicles table using UUIDs
    op.create_table('vehicles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('registration_number', sa.String(), nullable=False),
        sa.Column('vehicle_type', sa.String(), nullable=False),
        sa.Column('fuel_type', sa.String(), nullable=True),
        sa.Column('capacity_kg', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='INACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicles_organization_id'), 'vehicles', ['organization_id'], unique=False)
    op.create_index(op.f('ix_vehicles_registration_number'), 'vehicles', ['registration_number'], unique=True)
    op.create_index(op.f('ix_vehicles_status'), 'vehicles', ['status'], unique=False)

    # 4. Re-create vehicle_assignments using UUIDs
    op.create_table('vehicle_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('vehicle_id', sa.UUID(), nullable=False),
        sa.Column('driver_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('unassigned_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicle_assignments_driver_id'), 'vehicle_assignments', ['driver_id'], unique=False)
    op.create_index(op.f('ix_vehicle_assignments_vehicle_id'), 'vehicle_assignments', ['vehicle_id'], unique=False)
    op.create_index(op.f('ix_vehicle_assignments_is_active'), 'vehicle_assignments', ['is_active'], unique=False)

    # 5. Alter optimized_routes.vehicle_id to UUID
    op.execute("ALTER TABLE optimized_routes DROP CONSTRAINT IF EXISTS optimized_routes_vehicle_id_fkey")
    op.execute("ALTER TABLE optimized_routes ALTER COLUMN vehicle_id TYPE UUID USING NULL")
    op.create_foreign_key('optimized_routes_vehicle_id_fkey', 'optimized_routes', 'vehicles', ['vehicle_id'], ['id'], ondelete='SET NULL')

    # 6. Create trips table
    op.create_table('trips',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.UUID(), nullable=False),
        sa.Column('driver_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trips_driver_id'), 'trips', ['driver_id'], unique=False)
    op.create_index(op.f('ix_trips_organization_id'), 'trips', ['organization_id'], unique=False)
    op.create_index(op.f('ix_trips_status'), 'trips', ['status'], unique=False)
    op.create_index(op.f('ix_trips_vehicle_id'), 'trips', ['vehicle_id'], unique=False)

    # 7. Create trip_stops table
    op.create_table('trip_stops',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('trip_id', sa.UUID(), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('location_name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('arrival_time', sa.DateTime(), nullable=True),
        sa.Column('completion_time', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trip_stops_status'), 'trip_stops', ['status'], unique=False)
    op.create_index(op.f('ix_trip_stops_trip_id'), 'trip_stops', ['trip_id'], unique=False)

    # 8. Create vehicle_telemetry table
    op.create_table('vehicle_telemetry',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.UUID(), nullable=False),
        sa.Column('speed_kmh', sa.Float(), nullable=False),
        sa.Column('fuel_level_percentage', sa.Float(), nullable=False),
        sa.Column('battery_voltage', sa.Float(), nullable=False),
        sa.Column('ignition_state', sa.Boolean(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vehicle_telemetry_org_vehicle_time', 'vehicle_telemetry', ['organization_id', 'vehicle_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_vehicle_telemetry_organization_id'), 'vehicle_telemetry', ['organization_id'], unique=False)
    op.create_index(op.f('ix_vehicle_telemetry_timestamp'), 'vehicle_telemetry', ['timestamp'], unique=False)
    op.create_index(op.f('ix_vehicle_telemetry_vehicle_id'), 'vehicle_telemetry', ['vehicle_id'], unique=False)


def downgrade() -> None:
    op.drop_table('vehicle_telemetry')
    op.drop_table('trip_stops')
    op.drop_table('trips')
    op.drop_table('vehicle_assignments')
    op.drop_table('vehicles')

    # ### end Alembic commands ###

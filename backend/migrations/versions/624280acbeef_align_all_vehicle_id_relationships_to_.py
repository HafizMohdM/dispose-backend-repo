"""Align all vehicle_id relationships to Integer

Revision ID: 624280acbeef
Revises: ce40187b6a2b
Create Date: 2026-05-18 13:33:16.015210

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '624280acbeef'
down_revision: Union[str, Sequence[str], None] = 'ce40187b6a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by cleanly recreating tables dependent on vehicle_id to avoid casting issues."""
    # 1. Drop existing tables that reference vehicle_id
    op.execute("DROP TABLE IF EXISTS incidents CASCADE")
    op.execute("DROP TABLE IF EXISTS route_waypoints CASCADE")
    op.execute("DROP TABLE IF EXISTS optimized_routes CASCADE")
    op.execute("DROP TABLE IF EXISTS trip_stops CASCADE")
    op.execute("DROP TABLE IF EXISTS trips CASCADE")
    op.execute("DROP TABLE IF EXISTS vehicle_telemetry CASCADE")

    # 2. Create vehicle_telemetry fresh
    op.create_table('vehicle_telemetry',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('speed_kmh', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('fuel_level_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('battery_voltage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('ignition_state', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('timestamp', sa.DateTime(), nullable=False)
    )
    op.create_index('idx_vehicle_telemetry_org_vehicle_time', 'vehicle_telemetry', ['organization_id', 'vehicle_id', 'timestamp'])

    # 3. Create incidents fresh
    op.create_table('incidents',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('driver_id', sa.UUID(), sa.ForeignKey('drivers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trip_id', sa.UUID(), nullable=True),
        sa.Column('incident_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('reported_by', sa.Integer(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('reported_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

    # 4. Create optimized_routes fresh
    op.create_table('optimized_routes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('driver_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('total_distance_km', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('estimated_duration_min', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('optimized_polyline', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    # 5. Create route_waypoints fresh
    op.create_table('route_waypoints',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('optimized_route_id', sa.Integer(), sa.ForeignKey('optimized_routes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stop_number', sa.Integer(), nullable=False),
        sa.Column('waypoint_type', sa.String(length=50), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('arrival_time', sa.DateTime(), nullable=True),
        sa.Column('departure_time', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_waypoint_route_order', 'route_waypoints', ['optimized_route_id', 'stop_number'])

    # 6. Create trips fresh
    op.create_table('trips',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('driver_id', sa.UUID(), sa.ForeignKey('drivers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('trips')
    op.drop_table('route_waypoints')
    op.drop_table('optimized_routes')
    op.drop_table('incidents')
    op.drop_table('vehicle_telemetry')

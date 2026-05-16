"""
driver_tracking_routes.py — WebSocket route handlers for real-time driver GPS tracking.

Connection lifecycle:
  1. Driver connects → fetch their active IN_PROGRESS pickup from DB (ONCE).
  2. If a pickup exists, register its destination into manager.active_trips cache.
  3. On each GPS ping, call manager.process_location_update — pure in-memory math,
     no further DB queries.
  4. DB is written via a SHORT-LIVED session per ping (prevents stale session on long WS).
  5. On disconnect, manager.disconnect_driver clears the trip state cache.

Production considerations:
  - PickupAssignment.driver_id is Integer (FK to users.id), not the UUID from drivers table.
    The WebSocket path param driver_id represents a user ID (int), cast accordingly.
  - get_db() yields a generator-based session that dies when the handler exits. For a WebSocket
    that stays open for hours, we create fresh sessions per DB write to avoid stale connections.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.websockets.driver_tracking import manager
from app.services.driver_service import DriverService
from app.models.pickup import Pickup, PickupStatus
from app.models.pickup_assignment import PickupAssignment

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: Fetch Active Pickup Destination (DB query — called ONCE on connect)
# ---------------------------------------------------------------------------

def _get_active_pickup_for_driver(
    db: Session,
    driver_id_int: int,
) -> Optional[dict]:
    """
    Query the database for the driver's currently active (IN_PROGRESS) pickup
    and return its destination coordinates and ID.

    This is intentionally called ONCE when the WebSocket connects, not on
    every GPS ping. The result is cached in manager.active_trips.

    Args:
        db: Active database session.
        driver_id_int: The user ID (integer) of the driver, matching
                       PickupAssignment.driver_id FK to users.id.

    Returns:
        A dict with {pickup_id, latitude, longitude, organization_id} or None.
    """
    result = (
        db.query(Pickup)
        .join(PickupAssignment, PickupAssignment.pickup_id == Pickup.id)
        .filter(
            PickupAssignment.driver_id == driver_id_int,
            Pickup.status == PickupStatus.IN_PROGRESS,
        )
        .first()
    )

    if result is None:
        return None

    return {
        "pickup_id": result.id,
        "latitude": result.latitude,
        "longitude": result.longitude,
        "organization_id": result.organization_id,
    }


# ---------------------------------------------------------------------------
# Helper: Persist location with a short-lived session (anti-stale-session)
# ---------------------------------------------------------------------------

def _persist_driver_location(
    driver_id: str,
    organization_id: int,
    lat: float,
    lng: float,
    accuracy: Optional[float],
) -> None:
    """
    Write the driver's GPS coordinates to the driver_locations history table
    using a fresh, short-lived DB session.

    This avoids the stale-session problem that occurs when a single get_db()
    session is held open across a WebSocket connection lasting hours. Each
    write gets its own session → commit → close cycle.

    Failures are logged but do NOT crash the WebSocket loop — realtime
    broadcast is prioritized over history persistence.
    """
    db = SessionLocal()
    try:
        service = DriverService(db)
        service.update_driver_location(
            driver_id=driver_id,
            organization_id=organization_id,
            latitude=lat,
            longitude=lng,
            accuracy=accuracy,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(
            f"[GPS_PERSIST_FAIL] Driver {driver_id}: DB write failed — {e}. "
            f"Realtime broadcast will continue."
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# WebSocket: Dispatcher Dashboard
# ---------------------------------------------------------------------------

@router.websocket("/ws/dispatchers/{organization_id}")
async def dispatcher_ws(
    websocket: WebSocket,
    organization_id: int,
) -> None:
    """
    Dispatcher subscribes to receive enriched live location updates
    (including distance_meters and eta_minutes) for all active drivers
    in their organization.
    """
    await manager.connect_dispatcher(organization_id, websocket)

    try:
        while True:
            # Keep the connection alive; dispatcher is a pure subscriber
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_dispatcher(organization_id, websocket)


# ---------------------------------------------------------------------------
# WebSocket: Driver GPS Feed
# ---------------------------------------------------------------------------

@router.websocket("/ws/drivers/{driver_id}/{organization_id}")
async def driver_ws(
    websocket: WebSocket,
    driver_id: str,
    organization_id: int,
) -> None:
    """
    Driver mobile app streams GPS coordinates here.

    On connect:
      - Fetches the driver's active IN_PROGRESS pickup from DB (single query).
      - Registers destination into manager.active_trips for in-memory geofencing.

    On each ping:
      - Writes the raw location to DB via a fresh short-lived session.
      - Calls process_location_update for Haversine + geofence + ETA + broadcast.

    Expected incoming message format (JSON):
      {
        "lat": 12.9716,
        "lng": 77.5946,
        "accuracy": 10.5   # optional, in meters
      }
    """
    await manager.connect_driver(driver_id, websocket)

    # ---- Single DB query on connect: cache destination for geofencing ----
    # Use a short-lived session for the initial lookup too.
    init_db = SessionLocal()
    try:
        # Cast driver_id to int for the PickupAssignment.driver_id (FK to users.id)
        try:
            driver_id_int = int(driver_id)
        except (ValueError, TypeError):
            # If driver_id is a UUID string from the drivers table, 
            # the assignment query won't match anything — geofencing just won't activate.
            driver_id_int = None

        if driver_id_int is not None:
            active_pickup = _get_active_pickup_for_driver(init_db, driver_id_int)
        else:
            active_pickup = None

        if active_pickup:
            manager.register_trip(
                driver_id=driver_id,
                pickup_id=active_pickup["pickup_id"],
                organization_id=active_pickup["organization_id"],
                dest_lat=active_pickup["latitude"],
                dest_lng=active_pickup["longitude"],
            )
        else:
            logger.info(f"[WS_CONNECT] Driver {driver_id}: No active IN_PROGRESS pickup found. Geofencing inactive.")
    finally:
        init_db.close()

    # ---- Main GPS Ping Loop ----
    try:
        while True:
            raw = await websocket.receive_text()

            # Guard against malformed JSON — skip the ping, keep the connection alive
            try:
                payload = json.loads(raw)
                lat = float(payload["lat"])
                lng = float(payload["lng"])
                accuracy: Optional[float] = payload.get("accuracy")
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as parse_err:
                logger.warning(f"[GPS_PARSE_ERROR] Driver {driver_id}: Invalid payload — {parse_err}. Skipping ping.")
                continue

            # 1. Persist to DB via short-lived session (non-blocking on failure)
            _persist_driver_location(
                driver_id=driver_id,
                organization_id=organization_id,
                lat=lat,
                lng=lng,
                accuracy=accuracy,
            )

            # 2. In-memory geofencing + ETA + broadcast to dispatchers
            await manager.process_location_update(
                driver_id=driver_id,
                organization_id=organization_id,
                lat=lat,
                lng=lng,
            )

    except WebSocketDisconnect:
        manager.disconnect_driver(driver_id)

    except Exception as e:
        # Ensure cleanup even on unexpected errors
        logger.error(f"[WS_ERROR] Driver {driver_id}: Unexpected error — {e}")
        manager.disconnect_driver(driver_id)
        raise
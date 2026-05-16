"""
driver_tracking.py — Stateful WebSocket connection manager for live driver GPS tracking.

Architecture decisions:
  - Dispatchers subscribe per-organization; all drivers in that org push to them.
  - active_trips caches the destination coordinates + geofence state in memory.
    This eliminates DB queries on every GPS ping (anti-thrashing).
  - Geofencing, distance, and ETA are computed via pure in-memory Haversine math.
  - A "driver_arriving" pubsub event fires ONCE per trip when the geofence is breached.
  - Dead dispatcher connections are pruned on send failure to prevent accumulation.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.core.pubsub import pubsub_service
from app.utils.geo_utils import (
    GEOFENCE_RADIUS_METERS,
    calculate_eta_minutes,
    is_within_geofence,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-Memory Trip State Schema (stored per driver_id)
# ---------------------------------------------------------------------------
# {
#   "driver_id":           str,
#   "pickup_id":           int,
#   "organization_id":     int,
#   "dest_lat":            float,
#   "dest_lng":            float,
#   "geofence_triggered":  bool,   # True once fired; never fires again for this trip
# }
# ---------------------------------------------------------------------------


class DriverTrackingManager:
    """
    Manages WebSocket connections and in-memory trip state for real-time driver tracking.

    Connection pools:
        dispatchers: {organization_id -> [WebSocket, ...]}
        drivers:     {driver_id -> WebSocket}

    Trip state cache:
        active_trips: {driver_id -> trip_state_dict}
    """

    def __init__(self) -> None:
        self.dispatchers: Dict[int, List[WebSocket]] = {}
        self.drivers: Dict[str, WebSocket] = {}
        # Keyed by driver_id (str). Cached from DB once on connect; never queried per-ping.
        self.active_trips: Dict[str, dict] = {}

    # -----------------------------------------------------------------------
    # Connection Lifecycle — Drivers
    # -----------------------------------------------------------------------

    async def connect_driver(
        self,
        driver_id: str,
        websocket: WebSocket,
    ) -> None:
        """Accept a driver WebSocket connection and register it."""
        await websocket.accept()
        self.drivers[driver_id] = websocket
        logger.info(f"[WS_CONNECT] Driver {driver_id} connected.")

    def disconnect_driver(self, driver_id: str) -> None:
        """Remove the driver connection and purge its trip state."""
        self.drivers.pop(driver_id, None)
        self.active_trips.pop(driver_id, None)  # Clean up trip cache on disconnect
        logger.info(f"[WS_DISCONNECT] Driver {driver_id} disconnected. Trip state purged.")

    # -----------------------------------------------------------------------
    # Connection Lifecycle — Dispatchers
    # -----------------------------------------------------------------------

    async def connect_dispatcher(
        self,
        organization_id: int,
        websocket: WebSocket,
    ) -> None:
        """Accept a dispatcher WebSocket and subscribe it to the org's location feed."""
        await websocket.accept()
        if organization_id not in self.dispatchers:
            self.dispatchers[organization_id] = []
        self.dispatchers[organization_id].append(websocket)
        logger.info(f"[WS_CONNECT] Dispatcher connected to org {organization_id}. Total: {len(self.dispatchers[organization_id])}")

    def disconnect_dispatcher(
        self,
        organization_id: int,
        websocket: WebSocket,
    ) -> None:
        """Remove a dispatcher from the org's subscription list."""
        if organization_id in self.dispatchers:
            try:
                self.dispatchers[organization_id].remove(websocket)
            except ValueError:
                pass
            if not self.dispatchers[organization_id]:
                del self.dispatchers[organization_id]

    # -----------------------------------------------------------------------
    # Trip State Management
    # -----------------------------------------------------------------------

    def register_trip(
        self,
        driver_id: str,
        pickup_id: int,
        organization_id: int,
        dest_lat: float,
        dest_lng: float,
    ) -> None:
        """
        Cache the active trip's destination coordinates for in-memory geofencing.
        Called ONCE when the driver connects (after a DB lookup in the route handler).
        This avoids querying the database on every subsequent GPS ping.
        """
        self.active_trips[driver_id] = {
            "driver_id": driver_id,
            "pickup_id": pickup_id,
            "organization_id": organization_id,
            "dest_lat": dest_lat,
            "dest_lng": dest_lng,
            "geofence_triggered": False,  # Reset fresh for every new trip
        }
        logger.info(f"[TRIP_REGISTERED] Driver {driver_id} -> Pickup {pickup_id} @ ({dest_lat}, {dest_lng})")

    def clear_trip(self, driver_id: str) -> None:
        """Explicitly clear trip state (e.g., on pickup completion)."""
        self.active_trips.pop(driver_id, None)

    def get_trip(self, driver_id: str) -> Optional[dict]:
        """Return the cached trip state for a driver, or None if no active trip."""
        return self.active_trips.get(driver_id)

    # -----------------------------------------------------------------------
    # Core: Process an Incoming GPS Ping
    # -----------------------------------------------------------------------

    async def process_location_update(
        self,
        driver_id: str,
        organization_id: int,
        lat: float,
        lng: float,
    ) -> dict:
        """
        Process a real-time GPS ping from a driver:
          1. Enrich the location payload with distance_meters and eta_minutes.
          2. Check geofence: if the driver is within GEOFENCE_RADIUS_METERS of the
             destination AND the geofence has not already been triggered for this
             trip, fire the "driver_arriving" pubsub event ONCE.
          3. Broadcast the enriched payload to all dispatchers in the org.

        Returns the final enriched location dict that was broadcast.
        """
        trip = self.active_trips.get(driver_id)

        # Build the base payload
        location_data: dict = {
            "driver_id": driver_id,
            "lat": lat,
            "lng": lng,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "distance_meters": None,
            "eta_minutes": None,
            "geofence_status": "no_active_trip",
        }

        if trip:
            # --- In-memory Haversine calculation (zero DB queries) ---
            inside_fence, distance_m = is_within_geofence(
                driver_lat=lat,
                driver_lng=lng,
                dest_lat=trip["dest_lat"],
                dest_lng=trip["dest_lng"],
                radius_meters=GEOFENCE_RADIUS_METERS,
            )
            eta_min = calculate_eta_minutes(distance_m)

            # Enrich the broadcast payload
            location_data["distance_meters"] = round(distance_m, 2)
            location_data["eta_minutes"] = round(eta_min, 2)
            location_data["pickup_id"] = trip["pickup_id"]
            location_data["geofence_status"] = "en_route"

            # --- Geofence Trigger: fires ONCE per trip ---
            if inside_fence and not trip["geofence_triggered"]:
                trip["geofence_triggered"] = True  # Latch — prevents re-firing
                location_data["geofence_status"] = "arriving"

                logger.info(
                    f"[GEOFENCE_TRIGGERED] Driver {driver_id} within {GEOFENCE_RADIUS_METERS}m "
                    f"of Pickup {trip['pickup_id']} (distance: {distance_m:.1f}m)"
                )

                asyncio.create_task(
                    pubsub_service.publish(
                        f"tracking:org_{trip['organization_id']}",
                        {
                            "event": "driver_arriving",
                            "driver_id": driver_id,
                            "pickup_id": trip["pickup_id"],
                            "organization_id": trip["organization_id"],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": {
                                "distance_meters": round(distance_m, 2),
                                "eta_minutes": round(eta_min, 2),
                                "geofence_radius_meters": GEOFENCE_RADIUS_METERS,
                                "driver_lat": lat,
                                "driver_lng": lng,
                                "dest_lat": trip["dest_lat"],
                                "dest_lng": trip["dest_lng"],
                            },
                        },
                    )
                )

            elif inside_fence and trip["geofence_triggered"]:
                # Already inside the fence and event was already fired
                location_data["geofence_status"] = "arrived"

        # Broadcast enriched payload to all org dispatchers
        await self.broadcast_location(organization_id, location_data)
        return location_data

    # -----------------------------------------------------------------------
    # Broadcast to Dispatchers (with dead connection pruning)
    # -----------------------------------------------------------------------

    async def broadcast_location(
        self,
        organization_id: int,
        location_data: dict,
    ) -> None:
        """
        Fan-out a location payload to all dispatcher WebSockets subscribed
        to the given organization. Dead connections are pruned immediately
        to prevent repeated failed sends on subsequent pings.
        """
        dispatcher_list = self.dispatchers.get(organization_id)
        if not dispatcher_list:
            return

        message = json.dumps(location_data, default=str)
        dead_connections: List[WebSocket] = []

        # Iterate over a snapshot to allow safe removal
        for dispatcher_ws in list(dispatcher_list):
            try:
                await dispatcher_ws.send_text(message)
            except Exception:
                # Mark dead connection for removal
                dead_connections.append(dispatcher_ws)

        # Prune dead connections to prevent accumulation
        for dead_ws in dead_connections:
            try:
                dispatcher_list.remove(dead_ws)
                logger.warning(f"[WS_PRUNED] Dead dispatcher connection removed from org {organization_id}.")
            except ValueError:
                pass

        # Clean up empty org entry
        if not dispatcher_list:
            self.dispatchers.pop(organization_id, None)


# Singleton — shared across all WebSocket route handlers
manager = DriverTrackingManager()
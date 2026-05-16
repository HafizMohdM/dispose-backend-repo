"""
geo_utils.py — Pure in-memory geodetic utilities.

All calculations are done using the Haversine formula with no database I/O.
This module is intentionally dependency-free and fully unit-testable.
"""

import math
from typing import Tuple

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

# Earth's mean radius in meters (WGS-84 approximation)
_EARTH_RADIUS_M: float = 6_371_000.0

# Geofencing: a driver is considered "arriving" within this radius
GEOFENCE_RADIUS_METERS: float = 200.0

# Assumed city-driving speed (30 km/h converted to m/s)
CITY_SPEED_MS: float = 30_000 / 3600  # ≈ 8.333 m/s


# -------------------------------------------------------------------------
# Core Haversine Formula
# -------------------------------------------------------------------------

def haversine_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    """
    Calculate the great-circle distance (in meters) between two GPS coordinates
    using the Haversine formula.

    Args:
        lat1: Latitude of point A  (decimal degrees)
        lng1: Longitude of point A (decimal degrees)
        lat2: Latitude of point B  (decimal degrees)
        lng2: Longitude of point B (decimal degrees)

    Returns:
        Distance in meters (float).
    """
    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS_M * c


# -------------------------------------------------------------------------
# ETA Calculator
# -------------------------------------------------------------------------

def calculate_eta_minutes(distance_meters: float, speed_ms: float = CITY_SPEED_MS) -> float:
    """
    Estimate the arrival time in minutes given a remaining distance and speed.

    Args:
        distance_meters: Remaining distance to the destination in meters.
        speed_ms:        Assumed travel speed in meters per second.
                         Defaults to CITY_SPEED_MS (30 km/h).

    Returns:
        ETA in minutes (float). Returns 0.0 if speed is zero or negative.
    """
    if speed_ms <= 0 or distance_meters <= 0:
        return 0.0
    return (distance_meters / speed_ms) / 60.0


# -------------------------------------------------------------------------
# Geofence Check
# -------------------------------------------------------------------------

def is_within_geofence(
    driver_lat: float,
    driver_lng: float,
    dest_lat: float,
    dest_lng: float,
    radius_meters: float = GEOFENCE_RADIUS_METERS,
) -> Tuple[bool, float]:
    """
    Determine whether a driver's position is within the geofence radius
    of a destination.

    Args:
        driver_lat:    Driver's current latitude.
        driver_lng:    Driver's current longitude.
        dest_lat:      Destination latitude.
        dest_lng:      Destination longitude.
        radius_meters: Geofence boundary radius in meters.

    Returns:
        A tuple of (is_inside: bool, distance_meters: float).
        The distance is always returned so it can be used for ETA regardless
        of whether the geofence was breached.
    """
    distance = haversine_distance(driver_lat, driver_lng, dest_lat, dest_lng)
    return (distance <= radius_meters, distance)

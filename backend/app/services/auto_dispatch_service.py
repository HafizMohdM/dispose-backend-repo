"""
auto_dispatch_service.py — Automated rules-based dispatch engine.

Provides the AutoDispatchEngine class which assigns PENDING pickups to the closest
AVAILABLE & ON_DUTY drivers using in-memory geodetic distance calculations.

Features:
- Concurrency Protection: Uses `with_for_update(skip_locked=True)` to prevent 
  double-dispatching across multiple concurrent cron workers.
- Zero-Regression: Bridges the `Driver` (UUID) to `User` (int) identity via mobile matching
  so that `PickupService.assign_driver` is called exactly as it expects.
- State Management: Uses `locked_user_ids` memory set to prevent the "Superman Bug" 
  (assigning multiple pickups to the same driver in one run).
- Fault Tolerance: Individual pickup assignment errors are caught and rolled back without
  crashing the batch (prevents the "Poison Pill Bug").
"""

import logging
from typing import Set, Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.pickup import Pickup, PickupStatus
from app.models.driver import Driver, DriverAvailability, DriverLocation
from app.models.user import User
from app.utils.enums import DriverStatus, DriverAvailabilityStatus
from app.api.v1.pickups.pickup_service import PickupService
from app.utils.geo_utils import haversine_distance

logger = logging.getLogger(__name__)


class AutoDispatchEngine:
    """
    Automated dispatch engine for assigning PENDING pickups to the closest available drivers.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_available_drivers_with_location(self, organization_id: int) -> List[Tuple[Driver, float, float, int]]:
        """
        Fetches all ACTIVE drivers in the organization who are AVAILABLE and ON_DUTY.
        Joins their latest GPS coordinates and matches them to their User account via mobile number.

        Returns:
            A list of tuples: (Driver, latitude, longitude, user_id)
        """
        # Subquery to get the latest DriverLocation for each driver using DISTINCT ON
        latest_locations_subq = (
            self.db.query(DriverLocation)
            .distinct(DriverLocation.driver_id)
            .order_by(DriverLocation.driver_id, DriverLocation.recorded_at.desc())
            .subquery()
        )

        # Main query: Driver -> Availability -> Location -> User (by mobile)
        results = (
            self.db.query(
                Driver, 
                latest_locations_subq.c.latitude, 
                latest_locations_subq.c.longitude, 
                User.id.label("user_id")
            )
            .join(DriverAvailability, DriverAvailability.driver_id == Driver.id)
            .join(User, User.mobile == Driver.mobile)
            .join(latest_locations_subq, latest_locations_subq.c.driver_id == Driver.id)
            .filter(
                Driver.organization_id == organization_id,
                Driver.status == DriverStatus.ACTIVE,
                DriverAvailability.status == DriverAvailabilityStatus.AVAILABLE,
                DriverAvailability.is_on_duty == True,
            )
            .all()
        )

        return results

    def run_dispatch_cycle(self, organization_id: int, system_user: User, batch_size: int = 50) -> int:
        """
        Executes a single run of the auto-dispatch engine for a given organization.

        1. Fetches a locked batch of PENDING pickups using skip_locked=True.
        2. Fetches all currently available drivers and their locations.
        3. Assigns each pickup to the closest available driver.
        4. Tracks assigned drivers in memory to prevent double-assignment in the same run.

        Args:
            organization_id: Target organization ID.
            system_user: The system User account to record as the actor.
            batch_size: Max number of pickups to process in this cycle.

        Returns:
            The number of successfully assigned pickups.
        """
        # 1. Fetch available drivers (Snapshot for this cycle)
        available_drivers = self.get_available_drivers_with_location(organization_id)
        
        if not available_drivers:
            logger.info(f"[AUTO_DISPATCH] No available drivers in org {organization_id}. Cycle skipped.")
            return 0

        # Memory cache to prevent the "Superman Bug" (1 driver getting 50 jobs instantly)
        # We track the user_id (int) since that is what PickupService expects.
        locked_user_ids: Set[int] = set()
        successful_assignments = 0

        # 2. Fetch PENDING pickups with Row-Level Locking (Concurrency Protection)
        # Using skip_locked=True ensures multiple cron workers don't deadlock on the same rows.
        pending_pickups = (
            self.db.query(Pickup)
            .filter(
                Pickup.organization_id == organization_id,
                Pickup.status == PickupStatus.PENDING,
            )
            .with_for_update(skip_locked=True)
            .limit(batch_size)
            .all()
        )

        if not pending_pickups:
            return 0

        logger.info(f"[AUTO_DISPATCH] Org {organization_id}: Found {len(pending_pickups)} pending pickups. Processing...")

        # 3. Process Pickups
        for pickup in pending_pickups:
            
            # Find the absolute closest driver who hasn't been assigned in this run
            best_driver_user_id: Optional[int] = None
            shortest_distance: float = float('inf')

            for driver, lat, lng, user_id in available_drivers:
                if user_id in locked_user_ids:
                    continue  # Driver already assigned a pickup in this cycle
                
                distance = haversine_distance(
                    lat1=pickup.latitude,
                    lng1=pickup.longitude,
                    lat2=lat,
                    lng2=lng,
                )

                if distance < shortest_distance:
                    shortest_distance = distance
                    best_driver_user_id = user_id

            if not best_driver_user_id:
                logger.info(f"[AUTO_DISPATCH] Pickup {pickup.id}: No remaining available drivers. Stopping cycle.")
                break # We ran out of available drivers in this batch

            # 4. Assign the pickup inside a fault-tolerant block (Poison Pill Protection)
            try:
                # PickupService.assign_driver expects db, pickup_id, driver_id(int User.id), user
                # We use best_driver_user_id which is the User.id mapping.
                PickupService.assign_driver(
                    db=self.db, 
                    pickup_id=pickup.id, 
                    driver_id=best_driver_user_id, 
                    user=system_user
                )
                
                # Lock the driver so they don't get assigned again in this exact cron run loop
                locked_user_ids.add(best_driver_user_id)
                successful_assignments += 1
                
                logger.info(f"[AUTO_DISPATCH] Pickup {pickup.id} assigned to User ID {best_driver_user_id} (Distance: {shortest_distance:.1f}m)")
                
            except Exception as e:
                # Roll back JUST this pickup's transaction and continue to the next one
                self.db.rollback()
                logger.error(f"[AUTO_DISPATCH] Failed to assign Pickup {pickup.id}: {e}")
                continue

        return successful_assignments

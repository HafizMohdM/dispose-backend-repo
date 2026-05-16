from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import csv
import io
import uuid

from app.repositories.pickup_repo import PickupRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.models.pickup import Pickup, PickupStatus, PickupPriority
from app.models.pickup_media import PickupMedia, MediaType
from app.models.subscription import SubscriptionStatus
from app.models.pickup_assignment import AssignmentStatus
from app.api.v1.pickups.pickup_schemas import PickupCreateRequest, PickupUpdateStatusRequest
from app.api.v1.pickups.pickup_workflow_schemas import (
    PickupCancelRequest,
    PickupRescheduleRequest,
    PickupRejectRequest,
    PickupCompleteRequest,
    BulkAssignRequest,
    BulkCancelRequest,
    BulkRescheduleRequest
)
from app.services.audit_service import log_event
from app.core.pubsub import pubsub_service
from app.services.realtime.realtime_dashboard_service import dashboard_throttler
import asyncio

from app.models.pickup_exception import PickupException
from app.services.supabase_client import supabase
from app.api.v1.pickups.pickup_exception_schemas import PickupExceptionCreateRequest
from app.repositories.pickup_exception_repo import PickupExceptionRepository

from app.repositories.pickup_activity_repo import PickupActivityRepository
from app.models.pickup_activity import ActivityType


class PickupService:

    @staticmethod
    def create_pickup(db: Session, organization, request: PickupCreateRequest) -> Pickup:
        # 1. Fetch ACTIVE subscription for organization
        sub = SubscriptionRepository.get_active_subscription(db, organization.id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active subscription found. Please subscribe to a plan.")
        
        # 2. Validate not expired
        if datetime.utcnow() > sub.end_date:
            SubscriptionRepository.update_subscription_status(db, sub.id, SubscriptionStatus.EXPIRED)
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription has expired.")

        # 3. Lock subscription_usage row and safely increment usage using the existing atomic validator
        try:
            # Reusing the tested atomic validator from the subscription module.
            from app.services.subscription_service import SubscriptionService
            incremented_usage = SubscriptionService.validate_and_increment_usage(
                db=db, 
                subscription_id=sub.id, 
                pickups=1, 
                weight=request.waste_weight, 
                drivers=0
            ) 
        except HTTPException as e:
            raise e
        except Exception as e:
            # If the atomic increment fails for an unforeseen reason, rollback everything to be safe
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process pickup due to a system error.")

        # 4. Create the pickup since usage was validated
        new_pickup = Pickup(
            organization_id=organization.id,
            subscription_id=sub.id,
            waste_type=request.waste_type,
            waste_weight=request.waste_weight,
            address=request.address,
            latitude=request.latitude,
            longitude=request.longitude,
            status=PickupStatus.PENDING,
            scheduled_at=request.scheduled_at
        )

        created_pickup = PickupRepository.create_pickup(db, new_pickup)
        
        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=created_pickup.id, 
            user_id=None, # System created / Org Context
            activity_type=ActivityType.CREATED, 
            description="Pickup was created and scheduled."
        )

        # 5. Commit atomic transaction
        db.commit() # Added commit to finalize the creation and the activity log
        db.refresh(created_pickup)
        
        # 6. Broadcast Realtime Event
        asyncio.create_task(pubsub_service.publish(
            f"analytics:org_{organization.id}",
            {
                "event": "pickup_created",
                "organization_id": organization.id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "pickup_id": created_pickup.id,
                    "waste_type": created_pickup.waste_type,
                    "status": "pending"
                }
            }
        ))
        
        # 7. Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, organization.id))
        
        return created_pickup

    @staticmethod
    def list_pickups_for_org(db: Session, organization_id: int, p_status: PickupStatus = None):
        return PickupRepository.list_org_pickups(db, organization_id, p_status)

    @staticmethod
    def list_pickups_for_driver(db: Session, driver_id: int, a_status: AssignmentStatus = None):
        return PickupRepository.list_driver_pickups(db, driver_id, a_status)

    @staticmethod
    def list_all_pickups(db: Session, p_status: PickupStatus = None):
        return PickupRepository.list_all_pickups(db, p_status)

    @staticmethod
    def get_pickup_by_id(db: Session, pickup_id: int):
        pickup = PickupRepository.get_pickup_by_id(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
        return pickup

    @staticmethod
    def update_pickup_status(db: Session, pickup_id: int, request: PickupUpdateStatusRequest, user, is_admin: bool):
        pickup = PickupService.get_pickup_by_id(db, pickup_id)
        
        # Validate permissions depending on the operation
        if not is_admin:
            # Validate driver owns the assignment if they are trying to mark it complete
            if request.status in [PickupStatus.IN_PROGRESS, PickupStatus.COMPLETED]:
                is_assigned = any(assignment.driver_id == user.id for assignment in pickup.assignments)
                if not is_assigned:
                    raise HTTPException(status_code=403, detail="You are not assigned to this pickup.")

        old_status = pickup.status
        new_status = request.status

        # Strict State Machine Transition Rules
        valid_transitions = {
            PickupStatus.PENDING: [PickupStatus.ASSIGNED, PickupStatus.CANCELLED],
            PickupStatus.ASSIGNED: [PickupStatus.IN_PROGRESS, PickupStatus.CANCELLED],
            PickupStatus.IN_PROGRESS: [PickupStatus.COMPLETED, PickupStatus.CANCELLED],
            PickupStatus.COMPLETED: [],
            PickupStatus.CANCELLED: []
        }

        if new_status not in valid_transitions.get(old_status, []):
            raise HTTPException(status_code=400, detail=f"Invalid transition from {old_status} to {new_status}")

        # If cancelled early, ideally we return the usage back. Note: If we do this, we need to lock the usage row again.
        if new_status == PickupStatus.CANCELLED and old_status != PickupStatus.COMPLETED:
            from app.services.subscription_service import SubscriptionService
            # Decrement securely
            try:
                SubscriptionService.validate_and_increment_usage(
                    db=db, 
                    subscription_id=pickup.subscription_id, 
                    pickups=-1, 
                    weight=-pickup.waste_weight, 
                    drivers=0
                )
            except Exception:
                # ignore decrement errors if subscription is missing/deleted
                pass

        updated_pickup = PickupRepository.update_pickup_status(db, pickup_id, new_status)
        
        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user.id, 
            activity_type=ActivityType.STATUS_UPDATED, 
            description=f"Status updated from {old_status.value} to {new_status.value}.",
            metadata_payload={"old_status": old_status.value, "new_status": new_status.value}
        )

        db.commit()
        db.refresh(updated_pickup)
        
        # Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, updated_pickup.organization_id))
        return updated_pickup

    @staticmethod
    def assign_driver(db: Session, pickup_id: int, driver_id: int, user=None):
        # NOTE: Added `user=None` to signature to prevent routing breaks, but captures user if passed.
        # 1. Validate pickup exists and is pending
        pickup = PickupService.get_pickup_by_id(db, pickup_id)
        if pickup.status != PickupStatus.PENDING:
            raise HTTPException(status_code=400, detail="Pickup must be PENDING to be assigned.")
            
        # 2. Assign Driver
        assignment = PickupRepository.assign_driver(db, pickup_id, driver_id)
        
        # 3. Transition Pickup state to ASSIGNED
        pickup.status = PickupStatus.ASSIGNED
        
        # --- INJECT TIMELINE ACTIVITY ---
        user_id = user.id if user else None
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user_id, 
            activity_type=ActivityType.ASSIGNED, 
            description=f"Driver ID {driver_id} was assigned to the pickup.",
            metadata_payload={"driver_id": driver_id}
        )

        db.commit()
        db.refresh(pickup)
        return assignment

    @staticmethod
    def cancel_pickup(db: Session, pickup_id: int, request: PickupCancelRequest, user):
        pickup = PickupRepository.get_with_lock(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
        
        if pickup.status not in [PickupStatus.PENDING, PickupStatus.ASSIGNED]:
            raise HTTPException(status_code=400, detail="Only PENDING or ASSIGNED pickups can be cancelled")

        # Rollback subscription usage
        from app.services.subscription_service import SubscriptionService
        try:
            SubscriptionService.validate_and_increment_usage(
                db=db, 
                subscription_id=pickup.subscription_id, 
                pickups=-1, 
                weight=-pickup.waste_weight, 
                drivers=0
            )
        except Exception:
            pass

        updated_pickup = PickupRepository.update_pickup_status(db, pickup_id, PickupStatus.CANCELLED)
        
        log_event(
            db=db, 
            user_id=user.id, 
            action="CANCEL", 
            org_id=pickup.organization_id, 
            metadata={"entity_type": "pickup", "pickup_id": pickup_id, "reason": request.cancellation_reason}
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user.id, 
            activity_type=ActivityType.STATUS_UPDATED, 
            description="Pickup was cancelled.",
            notes=request.cancellation_reason,
            metadata_payload={"new_status": "CANCELLED", "reason": request.cancellation_reason}
        )
        
        db.commit()
        db.refresh(updated_pickup)

        # Broadcast Realtime Event
        asyncio.create_task(pubsub_service.publish(
            f"analytics:org_{updated_pickup.organization_id}",
            {
                "event": "pickup_cancelled",
                "organization_id": updated_pickup.organization_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "pickup_id": updated_pickup.id,
                    "status": "cancelled"
                }
            }
        ))

        # Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, updated_pickup.organization_id))
        return updated_pickup

    @staticmethod
    def reschedule_pickup(db: Session, pickup_id: int, request: PickupRescheduleRequest, user):
        pickup = PickupRepository.get_with_lock(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
            
        if pickup.status not in [PickupStatus.PENDING, PickupStatus.ASSIGNED]:
            raise HTTPException(status_code=400, detail="Only PENDING or ASSIGNED pickups can be rescheduled")

        old_schedule = pickup.scheduled_at.isoformat() if pickup.scheduled_at else None
        
        updated_pickup = PickupRepository.update_schedule(db, pickup_id, request.new_scheduled_at)
        
        log_event(
            db=db, 
            user_id=user.id, 
            action="RESCHEDULE", 
            org_id=pickup.organization_id, 
            metadata={
                "entity_type": "pickup", 
                "pickup_id": pickup_id, 
                "old_schedule": old_schedule,
                "new_schedule": request.new_scheduled_at.isoformat(),
                "reason": request.reason
            }
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user.id, 
            activity_type=ActivityType.RESCHEDULED, 
            description=f"Pickup rescheduled from {old_schedule} to {request.new_scheduled_at.isoformat()}.",
            notes=request.reason,
            metadata_payload={"old_schedule": old_schedule, "new_schedule": request.new_scheduled_at.isoformat()}
        )
        
        db.commit()
        db.refresh(updated_pickup)
        # Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, updated_pickup.organization_id))
        return updated_pickup

    @staticmethod
    def accept_pickup(db: Session, pickup_id: int, user):
        pickup = PickupRepository.get_with_lock(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
            
        if pickup.status != PickupStatus.ASSIGNED:
            raise HTTPException(status_code=400, detail="Only ASSIGNED pickups can be accepted")

        is_assigned = any(assignment.driver_id == user.id for assignment in pickup.assignments)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="You are not assigned to this pickup")

        updated_pickup = PickupRepository.update_pickup_status(db, pickup_id, PickupStatus.IN_PROGRESS)
        
        log_event(
            db=db, 
            user_id=user.id, 
            action="ACCEPT_PICKUP", 
            org_id=pickup.organization_id, 
            metadata={"entity_type": "pickup", "pickup_id": pickup_id}
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user.id, 
            activity_type=ActivityType.STATUS_UPDATED, 
            description="Driver accepted the pickup. Status changed to IN_PROGRESS."
        )
        
        db.commit()
        db.refresh(updated_pickup)
        # Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, updated_pickup.organization_id))
        return updated_pickup

    @staticmethod
    def reject_pickup(db: Session, pickup_id: int, request: PickupRejectRequest, user):
        pickup = PickupRepository.get_with_lock(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
            
        if pickup.status != PickupStatus.ASSIGNED:
            raise HTTPException(status_code=400, detail="Only ASSIGNED pickups can be rejected")

        is_assigned = any(assignment.driver_id == user.id for assignment in pickup.assignments)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="You are not assigned to this pickup")

        PickupRepository.remove_assignment(db, pickup_id, user.id)
        updated_pickup = PickupRepository.update_pickup_status(db, pickup_id, PickupStatus.PENDING)
        
        log_event(
            db=db, 
            user_id=user.id, 
            action="REJECT_PICKUP", 
            org_id=pickup.organization_id, 
            metadata={"entity_type": "pickup", "pickup_id": pickup_id, "reason": request.reason}
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user.id, 
            activity_type=ActivityType.UNASSIGNED, 
            description="Driver rejected the pickup assignment.",
            notes=request.reason,
            metadata_payload={"reason": request.reason}
        )
        
        db.commit()
        db.refresh(updated_pickup)
        # Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, updated_pickup.organization_id))
        return updated_pickup

    @staticmethod
    def complete_pickup(db: Session, pickup_id: int, request: PickupCompleteRequest, user):
        pickup = PickupRepository.get_with_lock(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
            
        if pickup.status != PickupStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Only IN_PROGRESS pickups can be completed")

        is_assigned = any(assignment.driver_id == user.id for assignment in pickup.assignments)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="You are not assigned to this pickup")

        updated_pickup = PickupRepository.update_completion(db, pickup_id, request.actual_weight)
        
        log_event(
            db=db, 
            user_id=user.id, 
            action="COMPLETE_PICKUP", 
            org_id=pickup.organization_id, 
            metadata={"entity_type": "pickup", "pickup_id": pickup_id, "actual_weight": request.actual_weight, "notes": request.notes}
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=user.id, 
            activity_type=ActivityType.STATUS_UPDATED, 
            description=f"Pickup completed with actual weight {request.actual_weight} kg.",
            notes=request.notes,
            metadata_payload={"actual_weight": request.actual_weight}
        )
        
        db.commit()
        db.refresh(updated_pickup)

        # Broadcast Realtime Event
        asyncio.create_task(pubsub_service.publish(
            f"analytics:org_{updated_pickup.organization_id}",
            {
                "event": "pickup_completed",
                "organization_id": updated_pickup.organization_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "pickup_id": updated_pickup.id,
                    "actual_weight": updated_pickup.actual_weight,
                    "status": "completed"
                }
            }
        ))

        # Trigger Live Dashboard KPI Refresh
        asyncio.create_task(dashboard_throttler.trigger_update(db, updated_pickup.organization_id))
        return updated_pickup

    # ==================== EXCEPTION METHODS ====================

    @staticmethod
    def report_exception(
        db: Session, 
        pickup_id: int, 
        request: PickupExceptionCreateRequest, 
        reported_by_id: int
    ) -> PickupException:
        """
        Report an exception for a pickup (Gate locked, Customer not present, etc.)
        """
        # Validate pickup exists and is in valid state
        pickup = PickupService.get_pickup_by_id(db, pickup_id)
        
        # Optional: Restrict exceptions to certain statuses
        if pickup.status in [PickupStatus.COMPLETED, PickupStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Cannot report exception on completed or cancelled pickup"
            )

        exception = PickupExceptionRepository.create_exception(
            db=db,
            pickup_id=pickup_id,
            exception_type=request.exception_type,
            notes=request.notes,
            reported_by_id=reported_by_id
        )

        # Log the event
        log_event(
            db=db,
            user_id=reported_by_id,
            action="REPORT_EXCEPTION",
            org_id=pickup.organization_id,
            metadata={
                "entity_type": "pickup_exception",
                "pickup_id": pickup_id,
                "exception_type": request.exception_type.value,
                "notes": request.notes
            }
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=pickup_id, 
            user_id=reported_by_id, 
            activity_type=ActivityType.EXCEPTION_REPORTED, 
            description=f"Exception reported: {request.exception_type.value}",
            notes=request.notes,
            metadata_payload={"exception_type": request.exception_type.value, "exception_id": exception.id}
        )
        
        db.commit() # Added commit for the exception and timeline log to flush together

        # Trigger realtime update
        asyncio.create_task(dashboard_throttler.trigger_update(db, pickup.organization_id))

        return exception


    @staticmethod
    def resolve_exception(
        db: Session, 
        exception_id: int, 
        resolved_by_id: int
    ) -> PickupException:
        """
        Mark an exception as resolved
        """
        exception = PickupExceptionRepository.resolve_exception(
            db=db, 
            exception_id=exception_id, 
            resolved_by_id=resolved_by_id
        )

        # Get pickup for logging and realtime
        pickup = PickupService.get_pickup_by_id(db, exception.pickup_id)

        log_event(
            db=db,
            user_id=resolved_by_id,
            action="RESOLVE_EXCEPTION",
            org_id=pickup.organization_id,
            metadata={
                "entity_type": "pickup_exception",
                "exception_id": exception_id,
                "pickup_id": exception.pickup_id,
                "exception_type": exception.exception_type.value
            }
        )

        # --- INJECT TIMELINE ACTIVITY ---
        PickupActivityRepository.log_activity(
            db=db, 
            pickup_id=exception.pickup_id, 
            user_id=resolved_by_id, 
            activity_type=ActivityType.EXCEPTION_RESOLVED, 
            description=f"Exception resolved: {exception.exception_type.value}",
            metadata_payload={"exception_id": exception_id, "exception_type": exception.exception_type.value}
        )

        db.commit()

        asyncio.create_task(dashboard_throttler.trigger_update(db, pickup.organization_id))

        return exception

    # ==================== BULK OPERATION METHODS ====================

    @staticmethod
    def bulk_assign(db: Session, request: BulkAssignRequest, user) -> dict:
        """
        Atomically assign a single driver to multiple PENDING pickups.
        If ANY pickup fails validation, the ENTIRE transaction is rolled back.
        """
        affected_ids = []
        try:
            # 1. Acquire FOR UPDATE locks on all requested pickups in a single query
            pickups = db.query(Pickup).filter(
                Pickup.id.in_(request.pickup_ids)
            ).with_for_update().all()

            # 2. Validate all requested IDs were found
            found_ids = {p.id for p in pickups}
            missing_ids = set(request.pickup_ids) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pickup IDs not found: {sorted(missing_ids)}"
                )

            # 3. Validate every pickup is in PENDING state before any mutation
            for pickup in pickups:
                if pickup.status != PickupStatus.PENDING:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Pickup ID {pickup.id} is in '{pickup.status.value}' state. Only PENDING pickups can be assigned. Entire bulk operation aborted."
                    )

            # 4. Apply mutations: assign driver + transition state + log timeline
            for pickup in pickups:
                PickupRepository.assign_driver(db, pickup.id, request.driver_id)
                pickup.status = PickupStatus.ASSIGNED

                PickupActivityRepository.log_activity(
                    db=db,
                    pickup_id=pickup.id,
                    user_id=user.id,
                    activity_type=ActivityType.ASSIGNED,
                    description=f"[BULK] Driver ID {request.driver_id} was assigned to the pickup.",
                    metadata_payload={"driver_id": request.driver_id, "bulk_operation": True}
                )

                log_event(
                    db=db,
                    user_id=user.id,
                    action="BULK_ASSIGN",
                    org_id=pickup.organization_id,
                    metadata={"entity_type": "pickup", "pickup_id": pickup.id, "driver_id": request.driver_id}
                )

                affected_ids.append(pickup.id)

            # 5. Atomic commit — all or nothing
            db.commit()

            # 6. Fire observability hooks for all affected organizations
            org_ids = {p.organization_id for p in pickups}
            for org_id in org_ids:
                asyncio.create_task(pubsub_service.publish(
                    f"analytics:org_{org_id}",
                    {
                        "event": "bulk_assign",
                        "organization_id": org_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"pickup_ids": affected_ids, "driver_id": request.driver_id}
                    }
                ))
                asyncio.create_task(dashboard_throttler.trigger_update(db, org_id))

            return {
                "operation": "bulk_assign",
                "affected_count": len(affected_ids),
                "affected_pickup_ids": affected_ids,
                "details": {"driver_id": request.driver_id}
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Bulk assign failed due to a system error: {str(e)}"
            )

    @staticmethod
    def bulk_cancel(db: Session, request: BulkCancelRequest, user) -> dict:
        """
        Atomically cancel multiple PENDING or ASSIGNED pickups.
        Rolls back subscription usage for each cancelled pickup.
        If ANY pickup fails validation, the ENTIRE transaction is rolled back.
        """
        affected_ids = []
        try:
            # 1. Acquire FOR UPDATE locks on all requested pickups
            pickups = db.query(Pickup).filter(
                Pickup.id.in_(request.pickup_ids)
            ).with_for_update().all()

            # 2. Validate all requested IDs were found
            found_ids = {p.id for p in pickups}
            missing_ids = set(request.pickup_ids) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pickup IDs not found: {sorted(missing_ids)}"
                )

            # 3. Validate every pickup is in a cancellable state
            cancellable_states = [PickupStatus.PENDING, PickupStatus.ASSIGNED]
            for pickup in pickups:
                if pickup.status not in cancellable_states:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Pickup ID {pickup.id} is in '{pickup.status.value}' state. Only PENDING or ASSIGNED pickups can be cancelled. Entire bulk operation aborted."
                    )

            # 4. Apply mutations: cancel + rollback usage + log timeline
            from app.services.subscription_service import SubscriptionService
            for pickup in pickups:
                # Rollback subscription usage
                try:
                    SubscriptionService.validate_and_increment_usage(
                        db=db,
                        subscription_id=pickup.subscription_id,
                        pickups=-1,
                        weight=-pickup.waste_weight,
                        drivers=0
                    )
                except Exception:
                    # Ignore decrement errors if subscription is missing/deleted
                    pass

                PickupRepository.update_pickup_status(db, pickup.id, PickupStatus.CANCELLED)

                PickupActivityRepository.log_activity(
                    db=db,
                    pickup_id=pickup.id,
                    user_id=user.id,
                    activity_type=ActivityType.STATUS_UPDATED,
                    description="[BULK] Pickup was cancelled.",
                    notes=request.cancellation_reason,
                    metadata_payload={"new_status": "CANCELLED", "reason": request.cancellation_reason, "bulk_operation": True}
                )

                log_event(
                    db=db,
                    user_id=user.id,
                    action="BULK_CANCEL",
                    org_id=pickup.organization_id,
                    metadata={"entity_type": "pickup", "pickup_id": pickup.id, "reason": request.cancellation_reason}
                )

                affected_ids.append(pickup.id)

            # 5. Atomic commit
            db.commit()

            # 6. Fire observability hooks
            org_ids = {p.organization_id for p in pickups}
            for org_id in org_ids:
                asyncio.create_task(pubsub_service.publish(
                    f"analytics:org_{org_id}",
                    {
                        "event": "bulk_cancel",
                        "organization_id": org_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"pickup_ids": affected_ids, "reason": request.cancellation_reason}
                    }
                ))
                asyncio.create_task(dashboard_throttler.trigger_update(db, org_id))

            return {
                "operation": "bulk_cancel",
                "affected_count": len(affected_ids),
                "affected_pickup_ids": affected_ids,
                "details": {"reason": request.cancellation_reason}
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Bulk cancel failed due to a system error: {str(e)}"
            )

    @staticmethod
    def bulk_reschedule(db: Session, request: BulkRescheduleRequest, user) -> dict:
        """
        Atomically reschedule multiple PENDING or ASSIGNED pickups to a new date/time.
        If ANY pickup fails validation, the ENTIRE transaction is rolled back.
        """
        affected_ids = []
        try:
            # 1. Acquire FOR UPDATE locks on all requested pickups
            pickups = db.query(Pickup).filter(
                Pickup.id.in_(request.pickup_ids)
            ).with_for_update().all()

            # 2. Validate all requested IDs were found
            found_ids = {p.id for p in pickups}
            missing_ids = set(request.pickup_ids) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pickup IDs not found: {sorted(missing_ids)}"
                )

            # 3. Validate every pickup is in a reschedulable state
            reschedulable_states = [PickupStatus.PENDING, PickupStatus.ASSIGNED]
            for pickup in pickups:
                if pickup.status not in reschedulable_states:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Pickup ID {pickup.id} is in '{pickup.status.value}' state. Only PENDING or ASSIGNED pickups can be rescheduled. Entire bulk operation aborted."
                    )

            # 4. Apply mutations: update schedule + log timeline
            for pickup in pickups:
                old_schedule = pickup.scheduled_at.isoformat() if pickup.scheduled_at else None

                PickupRepository.update_schedule(db, pickup.id, request.new_scheduled_at)

                PickupActivityRepository.log_activity(
                    db=db,
                    pickup_id=pickup.id,
                    user_id=user.id,
                    activity_type=ActivityType.RESCHEDULED,
                    description=f"[BULK] Pickup rescheduled from {old_schedule} to {request.new_scheduled_at.isoformat()}.",
                    notes=request.reason,
                    metadata_payload={
                        "old_schedule": old_schedule,
                        "new_schedule": request.new_scheduled_at.isoformat(),
                        "bulk_operation": True
                    }
                )

                log_event(
                    db=db,
                    user_id=user.id,
                    action="BULK_RESCHEDULE",
                    org_id=pickup.organization_id,
                    metadata={
                        "entity_type": "pickup",
                        "pickup_id": pickup.id,
                        "old_schedule": old_schedule,
                        "new_schedule": request.new_scheduled_at.isoformat(),
                        "reason": request.reason
                    }
                )

                affected_ids.append(pickup.id)

            # 5. Atomic commit
            db.commit()

            # 6. Fire observability hooks
            org_ids = {p.organization_id for p in pickups}
            for org_id in org_ids:
                asyncio.create_task(pubsub_service.publish(
                    f"analytics:org_{org_id}",
                    {
                        "event": "bulk_reschedule",
                        "organization_id": org_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "pickup_ids": affected_ids,
                            "new_scheduled_at": request.new_scheduled_at.isoformat(),
                            "reason": request.reason
                        }
                    }
                ))
                asyncio.create_task(dashboard_throttler.trigger_update(db, org_id))

            return {
                "operation": "bulk_reschedule",
                "affected_count": len(affected_ids),
                "affected_pickup_ids": affected_ids,
                "details": {
                    "new_scheduled_at": request.new_scheduled_at.isoformat(),
                    "reason": request.reason
                }
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Bulk reschedule failed due to a system error: {str(e)}"
            )

    @staticmethod
    def upload_pickup_image(db: Session, pickup_id: int, file: UploadFile, user) -> "PickupMedia":
        ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, and WebP are allowed.")
            
        file_bytes = file.file.read()
        if len(file_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Payload Too Large. Maximum file size is 5MB.")
            
        pickup = PickupRepository.get_pickup_by_id(db, pickup_id)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
            
        file_name = f"{uuid.uuid4()}_{file.filename}"
        path = f"pickups/{pickup.organization_id}/{pickup_id}/{file_name}"
        
        try:
            supabase.storage.from_("media").upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": file.content_type}
            )
            media_url = supabase.storage.from_("media").get_public_url(path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image upload failed: {e}")
            
        new_media = PickupMedia(
            pickup_id=pickup_id,
            media_url=media_url,
            media_type=MediaType.IMAGE
        )
        db.add(new_media)
        
        PickupActivityRepository.log_activity(
            db=db,
            pickup_id=pickup_id,
            user_id=user.id if user else None,
            activity_type=ActivityType.UPDATED,
            description="Uploaded proof image.",
            metadata_payload={"media_url": media_url}
        )
        db.commit()
        db.refresh(new_media)
        return new_media

    @staticmethod
    def import_csv(db: Session, organization_id: int, file: UploadFile, user) -> int:
        from app.repositories.subscription_repo import SubscriptionRepository
        from app.services.subscription_service import SubscriptionService
        
        sub = SubscriptionRepository.get_active_subscription(db, organization_id)
        if not sub:
            raise HTTPException(status_code=403, detail="No active subscription found.")

        content = file.file.read().decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(content))
        
        pickups_to_insert = []
        total_weight = 0.0
        for row in csv_reader:
            try:
                weight = float(row["waste_weight"])
                total_weight += weight
                pickup = Pickup(
                    organization_id=organization_id,
                    subscription_id=sub.id,
                    waste_type=row["waste_type"],
                    waste_weight=weight,
                    address=row["address"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    priority=row.get("priority", "NORMAL")
                )
                pickups_to_insert.append(pickup)
            except (KeyError, ValueError) as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Invalid CSV format at row: {row}. Error: {e}")
                
        if not pickups_to_insert:
            return 0
            
        total_pickups = len(pickups_to_insert)
            
        try:
            SubscriptionService.validate_and_increment_usage(
                db=db, 
                subscription_id=sub.id, 
                pickups=total_pickups, 
                weight=total_weight, 
                drivers=0
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=403, detail=str(e))
                
        try:
            PickupRepository.bulk_insert_pickups(db, pickups_to_insert)
            for p in pickups_to_insert:
                PickupActivityRepository.log_activity(
                    db=db,
                    pickup_id=p.id,
                    user_id=user.id if user else None,
                    activity_type=ActivityType.CREATED,
                    description="Pickup imported via CSV bulk upload."
                )
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to import batch: {e}")
            
        return len(pickups_to_insert)

    @staticmethod
    def export_csv(db: Session, organization_id: int) -> str:
        pickups = PickupRepository.get_pickups_for_export(db, organization_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Waste Type", "Weight", "Address", "Status", "Priority", "Created At"])
        
        for p in pickups:
            writer.writerow([
                p.id, p.waste_type, p.waste_weight, p.address, 
                p.status.value if p.status else "", 
                p.priority.value if p.priority else "", 
                p.created_at.isoformat() if p.created_at else ""
            ])
            
        return output.getvalue()

    @staticmethod
    def update_priority(db: Session, pickup_id: int, priority: str, user) -> Pickup:
        pickup = PickupRepository.update_priority(db, pickup_id, priority)
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup not found")
            
        PickupActivityRepository.log_activity(
            db=db,
            pickup_id=pickup_id,
            user_id=user.id if user else None,
            activity_type=ActivityType.UPDATED,
            description=f"Priority updated to {priority}",
            metadata_payload={"priority": priority}
        )
        
        db.commit()
        db.refresh(pickup)
        
        asyncio.create_task(pubsub_service.publish(f"org_{pickup.organization_id}", {
            "type": "pickup_updated",
            "pickup_id": pickup_id,
            "status": pickup.status.value,
            "priority": priority
        }))
        asyncio.create_task(dashboard_throttler.trigger_update(db, pickup.organization_id))
        
        return pickup

    @staticmethod
    def get_stats(db: Session, organization_id: int, start_date=None, end_date=None) -> dict:
        return PickupRepository.get_pickup_stats(db, organization_id, start_date, end_date)
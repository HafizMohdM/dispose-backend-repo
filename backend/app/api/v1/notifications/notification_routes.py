from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_organization
from app.core.permissions import require_permission
from app.services.notification_service import NotificationService
from app.utils.enums import NotificationStatus, NotificationSeverity, NotificationCategory

from app.api.v1.notifications.notification_schemas import (
    NotificationResponse,
    NotificationListResponse,
    NotificationReadResponse,
    NotificationReadAllResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    DeliveryLogResponse,
    DeliverySummaryResponse,
    UnreadCountResponse,
    NotificationMetricsResponse,
    TestNotificationRequest,
)

router = APIRouter()


@router.get(
    "",
    response_model=NotificationListResponse,
)
def get_notifications(
    status: Optional[NotificationStatus] = None,
    severity: Optional[NotificationSeverity] = None,
    category: Optional[NotificationCategory] = None,
    archived: Optional[bool] = False,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    service = NotificationService(db)

    notifications = service.get_user_notifications(
        organization_id=organization.id,
        user_id=current_user.id,
        status=status,
        severity=severity,
        category=category,
        archived=archived,
        search=search,
        skip=skip,
        limit=limit,
    )

    unread_count = service.get_unread_count(
        organization_id=organization.id,
        user_id=current_user.id,
        archived=archived,
    )

    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:update")),
):
    service = NotificationService(db)
    try:
        notification = service.mark_notification_read(
            notification_id=notification_id,
            organization_id=organization.id,
            user_id=current_user.id,
        )
        db.commit()
        return {
            "success": True,
            "notification_id": notification.id,
        }
    except Exception as e:
        db.rollback()
        raise e


@router.patch(
    "/read-all",
    response_model=NotificationReadAllResponse,
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:update")),
):
    service = NotificationService(db)
    try:
        count = service.mark_all_notifications_read(
            organization_id=organization.id,
            user_id=current_user.id,
        )
        db.commit()
        return {
            "success": True,
            "count": count,
        }
    except Exception as e:
        db.rollback()
        raise e


@router.patch(
    "/{notification_id}/archive",
    response_model=NotificationReadResponse,
)
def archive_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:update")),
):
    service = NotificationService(db)
    try:
        notification = service.archive_notification(
            notification_id=notification_id,
            organization_id=organization.id,
            user_id=current_user.id,
        )
        db.commit()
        return {
            "success": True,
            "notification_id": notification.id,
        }
    except Exception as e:
        db.rollback()
        raise e


@router.patch(
    "/archive-all",
    response_model=NotificationReadAllResponse,
)
def archive_all_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:update")),
):
    service = NotificationService(db)
    try:
        count = service.archive_all_notifications(
            organization_id=organization.id,
            user_id=current_user.id,
        )
        db.commit()
        return {
            "success": True,
            "count": count,
        }
    except Exception as e:
        db.rollback()
        raise e


@router.get(
    "/preferences",
    response_model=List[NotificationPreferenceResponse],
)
def get_user_preferences(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    service = NotificationService(db)
    return service.get_user_preferences(
        user_id=current_user.id,
        organization_id=organization.id,
    )


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def update_user_preference(
    pref_update: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:update")),
):
    service = NotificationService(db)
    try:
        pref = service.update_user_preference(
            user_id=current_user.id,
            organization_id=organization.id,
            category=pref_update.category,
            in_app_enabled=pref_update.in_app_enabled,
            email_enabled=pref_update.email_enabled,
            push_enabled=pref_update.push_enabled,
        )
        db.commit()
        return pref
    except Exception as e:
        db.rollback()
        raise e


@router.get(
    "/delivery-summary",
    response_model=DeliverySummaryResponse,
)
def get_delivery_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    """Get aggregated delivery statistics across all channels."""
    service = NotificationService(db)
    summary = service.get_delivery_summary(
        organization_id=organization.id,
        user_id=current_user.id,
    )
    return {"summary": summary}


@router.get(
    "/{notification_id}/delivery-logs",
    response_model=List[DeliveryLogResponse],
)
def get_delivery_logs(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    """Get delivery logs for a specific notification."""
    service = NotificationService(db)
    logs = service.get_delivery_logs(notification_id=notification_id)
    return logs


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=List[NotificationResponse],
)
def get_entity_notifications(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    service = NotificationService(db)
    notifications = service.get_entity_notifications(
        organization_id=organization.id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return notifications


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
def get_unread_count_only(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    """Fast endpoint returning only unread notifications count."""
    service = NotificationService(db)
    count = service.get_unread_count(
        organization_id=organization.id,
        user_id=current_user.id,
    )
    return {"unread_count": count}


@router.get(
    "/archived",
    response_model=NotificationListResponse,
)
def get_archived_notifications(
    status: Optional[NotificationStatus] = None,
    severity: Optional[NotificationSeverity] = None,
    category: Optional[NotificationCategory] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:view")),
):
    """Get paginated list of archived notifications with full-text search + filters consistency."""
    service = NotificationService(db)
    notifications = service.get_user_notifications(
        organization_id=organization.id,
        user_id=current_user.id,
        status=status,
        severity=severity,
        category=category,
        archived=True,
        search=search,
        skip=skip,
        limit=limit,
    )
    unread_count = service.get_unread_count(
        organization_id=organization.id,
        user_id=current_user.id,
        archived=True,
    )
    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }


@router.get(
    "/metrics",
    response_model=NotificationMetricsResponse,
)
def get_notification_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:manage")),
):
    """Get complete notification delivery, read rate, and severity/category metrics (Admin protected)."""
    service = NotificationService(db)
    return service.get_notification_metrics(
        user_id=current_user.id,
        organization_id=organization.id,
    )


@router.post(
    "/test",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_notification(
    payload: TestNotificationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:manage")),
):
    """Admin endpoint to dispatch a real-time & multi-channel test notification (Admin protected)."""
    service = NotificationService(db)
    notification = await service.create_test_notification(
        organization_id=organization.id,
        user_id=current_user.id,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        category=payload.category,
    )
    return notification


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    organization=Depends(get_current_organization),
    _: bool = Depends(require_permission("notification:update")),
):
    """Permanently delete a notification."""
    service = NotificationService(db)
    success = service.delete_notification(
        notification_id=notification_id,
        organization_id=organization.id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied",
        )
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_organization
from app.core.permissions import require_permission

from app.services.notification_service import NotificationService

from app.api.v1.notifications.notification_schemas import (
    NotificationResponse,
    NotificationListResponse,
    NotificationReadResponse,
    NotificationReadAllResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
)
def get_notifications(
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
        skip=skip,
        limit=limit,
    )

    unread_count = service.get_unread_count(
        organization_id=organization.id,
        user_id=current_user.id,
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

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )



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

    count = service.mark_all_notifications_read(
        organization_id=organization.id,
        user_id=current_user.id,
    )

    db.commit()

    return {
        "success": True,
        "count": count,
    }



@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=list[NotificationResponse],
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
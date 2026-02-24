from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_organization
from app.core.permissions import require_permission

from app.services.media_service import MediaService
from app.api.v1.media.media_schemas import MediaResponse


router = APIRouter()


@router.post(
    "/upload",
    response_model=MediaResponse,
)
def upload_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("media:create")),
):

    service = MediaService(db)

    media = service.upload_file(
        organization_id=org.id,
        uploaded_by=user.id,
        file=file,
    )

    db.commit()

    return media


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
)
def get_media(
    media_id: UUID,
    db: Session = Depends(get_db),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("media:view")),
):

    service = MediaService(db)

    return service.get_media(media_id, org.id)


@router.delete(
    "/{media_id}",
)
def delete_media(
    media_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    org=Depends(get_current_organization),
    _: bool = Depends(require_permission("media:delete")),
):

    service = MediaService(db)

    service.delete_media(
        media_id,
        org.id,
        user.id,
    )

    db.commit()

    return {"success": True}

@router.get(
    "/{media_id}/url",
)
def get_media_signed_url(
    media_id:UUID,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
    org= Depends(get_current_organization),
    _:bool = Depends(require_permission("media:view")),
):
    service = MediaService(db)

    return service.get_signed_url(
        media_id=media_id,
        organization_id=org.id,
        expires_in=expires_in
    )
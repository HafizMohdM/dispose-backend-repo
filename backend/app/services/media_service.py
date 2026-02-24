import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.media import Media
from app.repositories.media_repo import MediaRepository
from app.services.supabase_client import supabase


class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MediaRepository(db)

    def upload_file(self, organization_id: int, uploaded_by: int | None, file: UploadFile) -> Media:
        file_name = file.filename or "unknown"
        unique_prefix = str(uuid.uuid4())[:8]
        relative_path = f"{organization_id}/{unique_prefix}_{file_name}"
        file_bytes = file.file.read()

        try:
            supabase.storage.from_("media").upload(
                path=relative_path,
                file=file_bytes,
                file_options={"content-type": file.content_type}
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Supabase upload failed: {str(e)}"
            )

        file_size = len(file_bytes)
        file_type = file.content_type or "application/octet-stream"

        media = Media(
            organization_id=organization_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_path=relative_path,
            file_type=file_type,
            file_size=file_size,
        )

        return self.repo.create(media)

    def get_media(self, media_id: uuid.UUID, org_id: int) -> Media:
        media = self.repo.get_by_id_and_org(media_id, org_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        return media

    def delete_media(self, media_id: uuid.UUID, org_id: int, user_id: int) -> None:
        media = self.repo.get_by_id_and_org(media_id, org_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        try:
            supabase.storage.from_("media").remove([media.file_path])
        except Exception:
            pass

        self.repo.delete(media)

    def get_signed_url(
        self,
        media_id,
        organization_id:int,
        expires_in:int=3600
    ):

    #secure signed URL 

        media = self.repo.get_by_id_and_org(media_id,organization_id)
        if not media:
            raise HTTPException(status_code=404,details ="Media not found")
        try:
            response = supabase.storage.from_("media").create_signed_url(
                path=media.file_path,
                expires_in=expires_in
            )

            signed_url = response.get("signedURL")

            if not signed_url:
                raise Exception("Failed to generate signed URL")
            return{
                "media_id": str(media_id),
                "url": signed_url,
                "expires_in": expires_in

            }
        except Exception as e:
            raise HTTPException(status_code=500,details ="Failed to generate signed URL: " + str(e))

    


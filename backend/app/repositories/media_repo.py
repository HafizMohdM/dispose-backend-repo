from sqlalchemy.orm import Session
from uuid import UUID

from app.models.media import Media


class MediaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, media: Media) -> Media:
        self.db.add(media)
        self.db.flush()
        self.db.refresh(media)
        return media

    def get_by_id(self, media_id: UUID) -> Media | None:
        return self.db.query(Media).filter(Media.id == media_id).first()

    def get_by_id_and_org(self, media_id: UUID, org_id: int) -> Media | None:
        return self.db.query(Media).filter(
            Media.id == media_id,
            Media.organization_id == org_id
        ).first()

    def delete(self, media: Media):
        self.db.delete(media)
        self.db.flush()

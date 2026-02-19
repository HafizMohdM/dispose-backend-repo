from sqlalchemy.orm import Session
from app.models.organization import Organization


class OrganizationRepository:

    @staticmethod
    def create(db: Session, org: Organization):
        db.add(org)
        db.commit()
        db.refresh(org)
        return org

    @staticmethod
    def get_by_id(db: Session, org_id: int):
        return db.query(Organization).filter(Organization.id == org_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str):
        return db.query(Organization).filter(Organization.name == name).first()

    @staticmethod
    def get_all(db: Session, skip: int, limit: int):
        return db.query(Organization).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, org: Organization):
        db.commit()
        db.refresh(org)
        return org

    @staticmethod
    def update_fields(db: Session, org: Organization, update_data: dict):
        for field, value in update_data.items():
            setattr(org, field, value)
        db.commit()
        db.refresh(org)
        return org
from sqlalchemy.orm import Session
from app.models.organization import OrganizationCategory


class CategoryRepository:

    @staticmethod
    def create(db: Session, category: OrganizationCategory):
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def get_all(db: Session):
        return db.query(OrganizationCategory).all()

    @staticmethod
    def get_by_id(db: Session, category_id: int):
        return db.query(OrganizationCategory).filter(
            OrganizationCategory.id == category_id
        ).first()

    @staticmethod
    def update(db: Session, category, update_data: dict):
        for field, value in update_data.items():
            setattr(category, field, value)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def delete(db: Session, category):
        db.delete(category)
        db.commit()
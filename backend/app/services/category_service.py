from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.organization import OrganizationCategory
from app.repositories.category_repo import CategoryRepository


class CategoryService:

    @staticmethod
    def create_category(db: Session, data):
        category = OrganizationCategory(
            name=data.name,
            description=data.description
        )
        return CategoryRepository.create(db, category)

    @staticmethod
    def get_categories(db: Session):
        return CategoryRepository.get_all(db)

    @staticmethod
    def update_category(db: Session, category_id: int, data):
        category = CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        update_data = data.model_dump(exclude_unset=True)
        return CategoryRepository.update(db, category, update_data)

    @staticmethod
    def delete_category(db: Session, category_id: int):
        category = CategoryRepository.get_by_id(db, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        CategoryRepository.delete(db, category)
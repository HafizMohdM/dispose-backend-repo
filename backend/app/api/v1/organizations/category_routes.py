from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.category_service import CategoryService
from app.api.v1.organizations.category_schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse
)
from app.core.permissions import require_permission
from app.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/org-categories")


@router.post("", response_model=CategoryResponse)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.create"))
):
    return CategoryService.create_category(db, data)


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.view"))
):
    return CategoryService.get_categories(db)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.update"))
):
    return CategoryService.update_category(db, category_id, data)


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("category.delete"))
):
    CategoryService.delete_category(db, category_id)
    return {"message": "Category deleted successfully"}
from typing import Optional, List, TypeVar, Generic, Any
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Query
from sqlalchemy import desc, asc

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)

class DateFilterParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int

def paginate_query(query: Query, params: PaginationParams) -> dict:
    """
    Applies pagination to a SQLAlchemy query and returns metadata.
    """
    total = query.count()
    offset = (params.page - 1) * params.limit
    items = query.offset(offset).limit(params.limit).all()
    
    total_pages = (total + params.limit - 1) // params.limit
    
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "limit": params.limit,
        "total_pages": total_pages
    }

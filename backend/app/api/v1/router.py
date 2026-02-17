from fastapi import APIRouter
from app.api.v1.auth.auth_routes import router as auth_routes
from app.api.v1.admin.admin_routes import router as admin_router
api_router = APIRouter()

api_router.include_router(
    auth_routes,
    prefix="/auth",
    tags=["auth"]   
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin"]
)
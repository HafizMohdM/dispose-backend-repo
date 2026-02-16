from fastapi import APIRouter
from app.api.v1.auth.auth_routes import router as auth_routes

api_router = APIRouter()

api_router.include_router(
    auth_routes,
    prefix="/auth",
    tags=["auth"]   
)
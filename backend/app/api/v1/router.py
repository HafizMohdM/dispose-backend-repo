from fastapi import APIRouter
from app.api.v1.auth.auth_routes import router as auth_routes
from app.api.v1.admin.admin_routes import router as admin_router
from app.api.v1.organizations.org_routes import router as org_router
from app.api.v1.organizations.category_routes import router as category_router
from app.api.v1.subscriptions.subscription_routes import router as subscription_router
from app.api.v1.pickups.pickup_routes import router as pickup_router
from app.api.v1.drivers.driver_routes import router as driver_router
from app.api.v1.notifications.notification_routes import router as notification_router

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

api_router.include_router(
    org_router,
    prefix="/organizations",
    tags=["Organizations"]
)

api_router.include_router(
    category_router,
    prefix="/categories",
    tags=["Categories"]
)

api_router.include_router(
    driver_router,
    prefix="/drivers",
    tags=["Drivers"]
)
api_router.include_router(
    subscription_router,
)

api_router.include_router(
    pickup_router,
)

api_router.include_router(
    notification_router,
    prefix="/notifications",
    tags=["Notifications"]
)
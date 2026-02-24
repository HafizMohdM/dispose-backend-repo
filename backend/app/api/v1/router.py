from fastapi import APIRouter

api_router = APIRouter()


from app.api.v1.auth.auth_routes import router as auth_routes
from app.api.v1.admin.admin_routes import router as admin_router
from app.api.v1.organizations.org_routes import router as org_router
from app.api.v1.organizations.category_routes import router as category_router
from app.api.v1.subscriptions.subscription_routes import router as subscription_router
from app.api.v1.pickups.pickup_routes import router as pickup_router
from app.api.v1.drivers.driver_routes import router as driver_router
from app.api.v1.notifications.notification_routes import router as notification_router
from app.api.v1.audit.audit_route import router as audit_router
from app.api.v1.analytics.analytics_routes import router as analytics_router
from app.api.v1.media.media_routes import router as media_routes
from app.api.v1.admin.rbac_routes import router as rbac_router
from app.api.v1.system.system_setting_routes import router as system_setting_router
from app.api.v1.analytics.driver_analytics_routes import router as driver_analytics_router
from app.api.v1.websockets.driver_tracking_routes import router as ws_router



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
    rbac_router,
    prefix="/admin",
    tags=["Admin Roles & Permissions"]
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
    subscription_router,
)

api_router.include_router(
    driver_router,
    prefix="/drivers",
    tags=["Drivers"]
)


api_router.include_router(
    pickup_router,
)

api_router.include_router(
    media_routes,
    prefix="/media",
    tags=["Media"]
)

api_router.include_router(
    notification_router,
    prefix="/notifications",
    tags=["Notifications"]
)

api_router.include_router(
    audit_router,
    prefix="/audit-logs",
    tags=["Audit Logs"]
)

api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["Analytics"]
)

api_router.include_router(
    driver_analytics_router,
    prefix="/analytics/drivers",
    tags=["Driver Analytics"]
)

api_router.include_router(
    system_setting_router,
    prefix="/system-settings",
    tags=["System Settings"]
)

api_router.include_router(ws_router)












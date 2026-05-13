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
from app.api.v1.fleet.fleet_routes import router as fleet_router
from app.api.v1.map.map_routes import router as map_router
from app.api.v1.vehicles.vehicle_routes import router as vehicle_router
from app.api.v1.telemetry.telemetry_routes import router as telemetry_router
from app.api.v1.routes.route_optimization_routes import router as route_optimization_router
from app.api.v1.system.health_routes import router as health_router
from app.websocket.analytics_ws import router as analytics_ws_router
from app.websocket.dashboard_ws import router as dashboard_ws_router


from app.api.v1.drivers.mobile_routes import router as mobile_router
from app.api.v1.payments.payment_routes import router as payment_router



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
    mobile_router,
    prefix="/driver/app",
    tags=["Mobile Driver Experience"]
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
    prefix="/analytics"
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
api_router.include_router(
    payment_router
)
api_router.include_router(analytics_ws_router)
api_router.include_router(dashboard_ws_router)

# Fleet Intelligence System
api_router.include_router(fleet_router, prefix="/fleet", tags=["Fleet Intelligence"])
api_router.include_router(map_router, prefix="/map", tags=["Live Map System"])
api_router.include_router(vehicle_router, prefix="/vehicles", tags=["Vehicle Management System"])
api_router.include_router(telemetry_router, prefix="/telemetry", tags=["Telemetry Pipeline"])
api_router.include_router(route_optimization_router, prefix="/routes", tags=["Route Optimization Engine"])
api_router.include_router(health_router, prefix="/health", tags=["Observability & Health"])

api_router.include_router(ws_router)












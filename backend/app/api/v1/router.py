from fastapi import APIRouter

api_router = APIRouter()

# --- Router Imports ---
from app.api.v1.auth.auth_routes import router as auth_routes
from app.api.v1.auth.invitation_routes import router as invitation_router
from app.api.v1.admin.admin_routes import router as admin_router
from app.api.v1.organizations.org_routes import router as org_router
from app.api.v1.organizations.category_routes import router as category_router
from app.api.v1.organizations.member_routes import router as member_router
from app.api.v1.subscriptions.subscription_routes import router as subscription_router
from app.api.v1.pickups.pickup_routes import router as pickup_router
from app.api.v1.pickups.recurring_routes import router as recurring_router
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
from app.api.v1.trips.trip_routes import router as trip_router
from app.api.v1.incidents.incident_routes import router as incident_router
from app.api.v1.dashboard.dashboard_routes import router as dashboard_router
from app.api.v1.logistics.logistics_routes import router as logistics_router

# Production-level Tag Metadata for OpenAPI Documentation
TAGS_METADATA = [
    {
        "name": "Identity & Access",
        "description": "Handles authentication, role-based access control (RBAC), and user profile management.",
    },
    {
        "name": "Organization Management",
        "description": "Administrative tools for managing organizations, tenant categories, and member associations.",
    },
    {
        "name": "Fleet Intelligence",
        "description": "Real-time fleet tracking, vehicle diagnostics, and high-throughput telemetry data pipelines.",
    },
    {
        "name": "Logistics & Routing",
        "description": "Core logistics engine for pickup scheduling, TSP-based route optimization, and driver workflows.",
    },
    {
        "name": "Financials",
        "description": "Manages billing cycles, subscription plans, and secure payment processing.",
    },
    {
        "name": "Analytics & Insights",
        "description": "Executive dashboards providing deep insights into operational performance and growth.",
    },
    {
        "name": "System & Operations",
        "description": "Infrastructure-level services including notifications, audit trails, and service health monitoring.",
    },
]

# =============================================================================
# IDENTITY & ACCESS
# =============================================================================
api_router.include_router(
    auth_routes,
    prefix="/auth",
    tags=["Identity & Access"]
)
api_router.include_router(
    invitation_router,
    prefix="/invitations",
    tags=["Identity & Access"]
)
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Identity & Access"]
)
api_router.include_router(
    rbac_router,
    prefix="/admin/roles",
    tags=["Identity & Access"]
)

# =============================================================================
# ORGANIZATION MANAGEMENT
# =============================================================================
api_router.include_router(
    org_router,
    prefix="/organizations",
    tags=["Organization Management"]
)
api_router.include_router(
    member_router,
    prefix="/organizations/{org_id}/members",
    tags=["Organization Management"]
)
api_router.include_router(
    category_router,
    prefix="/categories",
    tags=["Organization Management"]
)

# =============================================================================
# LOGISTICS & ROUTING
# =============================================================================
api_router.include_router(
    pickup_router,
    prefix="/pickups",
    tags=["Logistics & Routing"]
)
api_router.include_router(
    recurring_router,
    prefix="/pickups/recurring",
    tags=["Logistics & Routing"]
)
api_router.include_router(
    route_optimization_router,
    prefix="/routes",
    tags=["Logistics & Routing"]
)
api_router.include_router(
    trip_router,
    prefix="/trips",
    tags=["Logistics & Routing"]
)
api_router.include_router(
    logistics_router,
    prefix="/logistics",
    tags=["Logistics & Routing"]
)

# =============================================================================
# FLEET INTELLIGENCE
# =============================================================================
api_router.include_router(
    driver_router,
    prefix="/drivers",
    tags=["Fleet Intelligence"]
)
api_router.include_router(
    mobile_router,
    prefix="/driver/app",
    tags=["Fleet Intelligence"]
)
api_router.include_router(
    fleet_router,
    prefix="/fleet",
    tags=["Fleet Intelligence"]
)
api_router.include_router(
    map_router,
    prefix="/map",
    tags=["Fleet Intelligence"]
)
api_router.include_router(
    vehicle_router,
    prefix="/vehicles",
    tags=["Fleet Intelligence"]
)
api_router.include_router(
    telemetry_router,
    prefix="/telemetry",
    tags=["Fleet Intelligence"]
)
api_router.include_router(
    incident_router,
    prefix="/incidents",
    tags=["Fleet Intelligence"]
)

# =============================================================================
# FINANCIALS
# =============================================================================
api_router.include_router(
    subscription_router,
    prefix="/subscription",
    tags=["Financials"]
)
api_router.include_router(
    payment_router,
    prefix="/payments",
    tags=["Financials"]
)

# =============================================================================
# ANALYTICS & INSIGHTS
# =============================================================================
api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["Analytics & Insights"]
)
api_router.include_router(
    driver_analytics_router,
    prefix="/analytics/drivers",
    tags=["Analytics & Insights"]
)
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Analytics & Insights"]
)

# =============================================================================
# SYSTEM & OPERATIONS
# =============================================================================
api_router.include_router(
    notification_router,
    prefix="/notifications",
    tags=["System & Operations"]
)
api_router.include_router(
    media_routes,
    prefix="/media",
    tags=["System & Operations"]
)
api_router.include_router(
    audit_router,
    prefix="/audit-logs",
    tags=["System & Operations"]
)
api_router.include_router(
    system_setting_router,
    prefix="/system-settings",
    tags=["System & Operations"]
)
api_router.include_router(
    health_router,
    prefix="/health",
    tags=["System & Operations"]
)

# =============================================================================
# REAL-TIME SYSTEMS (WEBSOCKETS)
# =============================================================================
api_router.include_router(ws_router, prefix="/ws/tracking", tags=["Fleet Intelligence"])
api_router.include_router(analytics_ws_router, prefix="/ws/analytics", tags=["Analytics & Insights"])
api_router.include_router(dashboard_ws_router, prefix="/ws/dashboard", tags=["Analytics & Insights"])

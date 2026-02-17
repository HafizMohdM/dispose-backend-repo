# RBAC seed constants

ROLES = [
    {"name": "ADMIN", "description": "Platform administrator"},
    {"name": "COMPANY", "description": "Organization operator"},
    {"name": "DRIVER", "description": "Pickup driver"},
    {"name": "CUSTOMER", "description": "Organization customer"},
]

PERMISSIONS = [
    {"code": "auth.login", "description": "Login to system"},
    {"code": "admin.access", "description": "Access admin panel"},
    {"code": "pickup.create", "description": "Create pickup request"},
    {"code": "pickup.view", "description": "View pickup details"},
    {"code": "pickup.assign", "description": "Assign pickup to driver"},
    {"code": "pickup.complete", "description": "Complete pickup"},
    {"code": "org.manage", "description": "Manage organization"},
    {"code": "report.view", "description": "View reports"},
]

ROLE_PERMISSIONS = {
    "ADMIN": [
        "auth.login",
        "admin.access",
        "org.manage", 
        "pickup.create", 
        "pickup.view",
        "pickup.assign", 
        "pickup.complete",
        "report.view"
    ],
    "COMPANY": ["auth.login", "pickup.create", "pickup.view", "report.view"],
    "DRIVER": ["auth.login", "pickup.view", "pickup.complete"],
    "CUSTOMER": ["auth.login", "pickup.create", "pickup.view"],
}

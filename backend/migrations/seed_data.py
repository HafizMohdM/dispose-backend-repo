# RBAC seed constants

ROLES = [
    {"name": "ADMIN", "description": "Platform administrator"},
    {"name": "COMPANY", "description": "Organization operator"},
    {"name": "DRIVER", "description": "Pickup driver"},
    {"name": "CUSTOMER", "description": "Organization customer"},
]

PERMISSIONS = [
    {"code": "auth.login", "description": "Login to system"},
    {"code": "pickup.create", "description": "Create pickup request"},
    {"code": "pickup.view", "description": "View pickup details"},
    {"code": "pickup.assign", "description": "Assign pickup to driver"},
    {"code": "pickup.complete", "description": "Complete pickup"},
    {"code": "org.manage", "description": "Manage organization"},
    {"code": "report.view", "description": "View reports"},
]
